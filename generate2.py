# coding: UTF-8

import sys
import math
import json
import xml.dom.minidom

def calcTime(pos):
	preLength = bpmInfo["preLength"]
	return (float(pos) + preLength) / 2

class NoteBase(object):
	def __init__(self, note, tp):
		self.line = int(note.getElementsByTagName('line{}'.format(tp))[0].childNodes[0].data) + 4
		self.pos = str(note.getElementsByTagName('pos{}'.format(tp))[0].childNodes[0].data)
		
	def generate(self, resultList, bpm):
		pass

# 单键，包括蓝键和灰键
class NoteN(NoteBase):
	def __init__(self, note, tp):
		super(NoteN, self).__init__(note, tp)
		
	def generate(self, resultList):
		resultList.append({
			"type": "Note",
			"lane": self.line,
			"beat": calcTime(self.pos),
			"note": "Single",
		})
		
# 粉键
class NoteF(NoteBase):
	def __init__(self, note, tp):
		super(NoteF, self).__init__(note, tp)
		
	def generate(self, resultList):
		resultList.append({
			"type": "Note",
			"lane": self.line,
			"beat": calcTime(self.pos),
			"note": "Single",
			"flick": True,
		})

# 滑条起点
class LineStart(NoteBase):
	def __init__(self, note, tp):
		super(LineStart, self).__init__(note, tp)
		self.lineInsts = []
		self.nextNode = None
		self.prevNode = None
		self.lineAB = None
		
	def addLineInst(self, nodeInst):
		self.lineInsts.append(nodeInst)
		
	def sortLineInst(self):
		# 将后续节点排序：
		self.lineInsts.sort(key=lambda nodeInst: float(nodeInst.pos))
		curNode = self
		nextNode = self.lineInsts[0]
		for nodeInst in self.lineInsts:
			curNode.nextNode = nextNode
			nextNode.prevNode = curNode
			curNode, nextNode = nextNode, nodeInst
		curNode.nextNode = nextNode
		nextNode.prevNode = curNode
		
	def generate(self, resultList):
		resultList.append({
			"type": "Note",
			"note": "Slide",
			"pos": self.lineAB,
			"start": True,
			"lane": self.line,
			"beat": calcTime(self.pos),
		})
		
	def setLineAB(self, ab):
		self.lineAB = ab
		for nodeInst in self.lineInsts:
			nodeInst.setLineAB(ab)
		ABDict.setdefault(self.pos, [])
		ABDict[self.pos].append("+{}".format(self.lineAB))
		ABList.append(self.pos)
		
# 滑条中间节点
class LineMiddle(NoteBase):
	def __init__(self, note, tp):
		super(LineMiddle, self).__init__(note, tp)
		self.startLine = int(note.getElementsByTagName('startlineL'.format(tp))[0].childNodes[0].data) + 4
		self.startPos = str(note.getElementsByTagName('startposL'.format(tp))[0].childNodes[0].data)
		self.nextNode = None
		self.prevNode = None
		self.lineAB = None
		
	def generate(self, resultList):
		resultList.append({
			"type": "Note",
			"note": "Slide",
			"pos": self.lineAB,
			"lane": self.line,
			"beat": calcTime(self.pos),
		})
		
	def setLineAB(self, ab):
		self.lineAB = ab
		
# 滑条终点N
class LineEndN(NoteBase):
	def __init__(self, note, tp):
		super(LineEndN, self).__init__(note, tp)
		self.startLine = int(note.getElementsByTagName('startlineL'.format(tp))[0].childNodes[0].data) + 4
		self.startPos = str(note.getElementsByTagName('startposL'.format(tp))[0].childNodes[0].data)
		self.nextNode = None
		self.prevNode = None
		self.lineAB = None
		
	def generate(self, resultList):
		resultList.append({
			"type": "Note",
			"note": "Slide",
			"pos": self.lineAB,
			"lane": self.line,
			"beat": calcTime(self.pos),
			"end": True,
		})
		
	def setLineAB(self, ab):
		self.lineAB = ab
		ABDict.setdefault(self.pos, [])
		ABDict[self.pos].append("-{}".format(self.lineAB))
		ABList.append(self.pos)

# 滑条终点F
class LineEndF(NoteBase):
	def __init__(self, note, tp):
		super(LineEndF, self).__init__(note, tp)
		self.startLine = int(note.getElementsByTagName('startlineL'.format(tp))[0].childNodes[0].data) + 4
		self.startPos = str(note.getElementsByTagName('startposL'.format(tp))[0].childNodes[0].data)
		self.nextNode = None
		self.prevNode = None
		self.lineAB = None
		
	def generate(self, resultList):
		resultList.append({
			"type": "Note",
			"note": "Slide",
			"pos": self.lineAB,
			"lane": self.line,
			"beat": calcTime(self.pos),
			"end": True,
			"flick": True,
		})
		
	def setLineAB(self, ab):
		self.lineAB = ab
		ABDict.setdefault(self.pos, [])
		ABDict[self.pos].append("-{}".format(self.lineAB))
		ABList.append(self.pos)
		

def getAB(pos):
	ABList.sort(key = lambda item: float(item))
	aAvail = True
	bAvail = True
	for ABPos in ABList:
		if float(pos) < float(ABPos):
			break
		ops = ABDict[ABPos]
		for op in ops:
			if op[0] == "+":
				if op[1] == "A":
					aAvail = False
				if op[1] == "B":
					bAvail = False
			elif op[0] == "-" and float(pos) > float(ABPos):
				if op[1] == "A":
					aAvail = True
				if op[1] == "B":
					bAvail = True
	return aAvail, bAvail

nodeTypeClsDict = {
	"N": NoteN,
	"F": NoteF,
	"LS": LineStart,
	"LM": LineMiddle,
	"LE": LineEndN,
	"LF": LineEndF,
}

# 读取sav文件：
document = xml.dom.minidom.parse("input.sav")
root = document.documentElement
types = ["N", "L", "F"]

noteMap = {}
lineSList = []
lineMEFList = []
bpmInfo = {}
ABDict = {}
ABList = []

info = root.getElementsByTagName("info")[0]
bpm = int(info.getElementsByTagName("bpm")[0].childNodes[0].data)
preLength = int(sys.argv[1])
bpmInfo["bpm"] = bpm
bpmInfo["preLength"] = preLength

for tp in types:
	nodeList = root.getElementsByTagName("note{}".format(tp))
	for note in nodeList:
		nodeType = note.getElementsByTagName('type{}'.format(tp))[0].childNodes[0].data
		nodeInst = nodeTypeClsDict[nodeType](note, tp)
		# 加入noteMap：
		noteMap.setdefault(nodeInst.pos, {})
		noteMap[nodeInst.pos][nodeInst.line] = nodeInst
		# 记录绿条中间节点与结束节点：
		if nodeType in ["LM", "LE", "LF"]:
			lineMEFList.append(nodeInst)
		elif nodeType == "LS":
			lineSList.append(nodeInst)
			
# 关联绿条：
for nodeInst in lineMEFList:
	startLine = nodeInst.startLine
	startPos = nodeInst.startPos
	startInst = noteMap[startPos][startLine]
	startInst.addLineInst(nodeInst)
for nodeInst in lineSList:
	nodeInst.sortLineInst()

# 增加A和B的标签：
lineSList.sort(key=lambda item: float(item.pos))
for nodeInst in lineSList:
	pos = nodeInst.pos
	aAvail, bAvail = getAB(pos)
	if aAvail:
		nodeInst.setLineAB("A")
	elif bAvail:
		nodeInst.setLineAB("B")

#开始生成json：
resultListMap = []
resultListMap.append({
	"type": "System",
	"cmd": "BPM",
	"beat": 0,
	"bpm": bpm,
})
times = noteMap.keys()
times.sort(key=lambda item: float(item))
for tm in times:
	notes = noteMap[tm]
	noteList = notes.values()
	for note in noteList:
		note.generate(resultListMap)
		
with open("output.txt", "wt") as output:
	json.dump(resultListMap, output)
