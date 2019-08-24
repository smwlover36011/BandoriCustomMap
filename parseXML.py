# coding: UTF-8

import xml.dom.minidom

def calcTime(pos, bpm):
	return 60.0 / (bpm * 2) * float(pos)
	
def isGrayNote(pos):
	return '.' in pos

class NoteBase(object):
	def __init__(self, note):
		self.line = int(note.getElementsByTagName('line{}'.format(tp))[0].childNodes[0].data) + 4
		self.pos = str(note.getElementsByTagName('pos{}'.format(tp))[0].childNodes[0].data)
		
	def generate(self, resultList, bpm):
		pass

# 单键，包括蓝键和灰键
# line: 1-7
# pos: 节拍数
class NoteN(NoteBase):
	def __init__(self, note):
		super(NoteN, self).__init__(note)
		
	def generate(self, resultList, bpm):
		resultList.append({
			"type": "SingleOff" if isGrayNote(self.pos) else "Single",
			"lane": self.line,
			"time": calcTime(self.pos, bpm),
		})

# 粉键
class NoteF(NoteBase):
	def __init__(self, note):
		super(NoteF, self).__init__(note)
		
	def generate(self, resultList, bpm):
		resultList.append({
			"type": "Flick",
			"lane": self.line,
			"time": calcTime(self.pos, bpm),
		})

# 滑条起点
# nextNote可以是LineMiddle，LineEndN和LineEndF
class LineStart(NoteBase):
	def __init__(self, note):
		super(LineStart, self).__init__(note)
		self.lineInsts = []
		self.nextNode = None
		self.prevNode = None
		
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
		
	def generate(self, resultList, bpm):
		resultList.append({
			"type": "Long",
			"lane": self.line,
			"time": calcTime(self.pos, bpm),
		})
		resultList.append({
			"type": "Bar",
			"lane": [self.line, self.nextNode.line],
			"time": [calcTime(self.pos, bpm), calcTime(self.nextNode.pos, bpm)],
		})

# 滑条中间节点
class LineMiddle(NoteBase):
	def __init__(self, note):
		super(LineMiddle, self).__init__(note)
		self.startLine = int(note.getElementsByTagName('startlineL'.format(tp))[0].childNodes[0].data) + 4
		self.startPos = str(note.getElementsByTagName('startposL'.format(tp))[0].childNodes[0].data)
		self.nextNode = None
		self.prevNode = None
		
	def generate(self, resultList, bpm):
		resultList.append({
			"type": "Tick",
			"lane": self.line,
			"time": calcTime(self.pos, bpm),
		})
		resultList.append({
			"type": "Bar",
			"lane": [self.line, self.nextNode.line],
			"time": [calcTime(self.pos, bpm), calcTime(self.nextNode.pos, bpm)],
		})

# 滑条终点N
class LineEndN(NoteBase):
	def __init__(self, note):
		super(LineEndN, self).__init__(note)
		self.startLine = int(note.getElementsByTagName('startlineL'.format(tp))[0].childNodes[0].data) + 4
		self.startPos = str(note.getElementsByTagName('startposL'.format(tp))[0].childNodes[0].data)
		self.nextNode = None
		self.prevNode = None
		
	def generate(self, resultList, bpm):
		resultList.append({
			"type": "Long",
			"lane": self.line,
			"time": calcTime(self.pos, bpm),
		})

# 滑条终点F
class LineEndF(NoteBase):
	def __init__(self, note):
		super(LineEndF, self).__init__(note)
		self.startLine = int(note.getElementsByTagName('startlineL'.format(tp))[0].childNodes[0].data) + 4
		self.startPos = str(note.getElementsByTagName('startposL'.format(tp))[0].childNodes[0].data)
		self.nextNode = None
		self.prevNode = None
		
	def generate(self, resultList, bpm):
		resultList.append({
			"type": "Flick",
			"lane": self.line,
			"time": calcTime(self.pos, bpm),
		})

nodeTypeClsDict = {
	"N": NoteN,
	"F": NoteF,
	"LS": LineStart,
	"LM": LineMiddle,
	"LE": LineEndN,
	"LF": LineEndF,
}


document = xml.dom.minidom.parse("super.sav")
root = document.documentElement
types = ["N", "L", "F"]

noteMap = {}
lineSList = []
lineMEFList = []

bpmInfo = root.getElementsByTagName("info")[0]
bpm = int(bpmInfo.getElementsByTagName("bpm")[0].childNodes[0].data)

for tp in types:
	nodeList = root.getElementsByTagName("note{}".format(tp))
	for note in nodeList:
		nodeType = note.getElementsByTagName('type{}'.format(tp))[0].childNodes[0].data
		nodeInst = nodeTypeClsDict[nodeType](note)
		# 加入noteMap：
		noteMap.setdefault(nodeInst.pos, {})
		noteMap[nodeInst.pos][nodeInst.line] = nodeInst
		# 记录绿条中间节点与结束节点：
		if nodeType in ["LM", "LE", "LF"]:
			lineMEFList.append(nodeInst)
		elif nodeType == "LS":
			lineSList.append(nodeInst)
		
#关联绿条：
for nodeInst in lineMEFList:
	startLine = nodeInst.startLine
	startPos = nodeInst.startPos
	startInst = noteMap[startPos][startLine]
	startInst.addLineInst(nodeInst)
for nodeInst in lineSList:
	nodeInst.sortLineInst()
	
#开始生成json：
resultList = []
times = noteMap.keys()
times.sort(key=lambda item: float(item))

import sys
if "-map" in sys.argv:
	resultList.append({
		"type": "BPM",
		"bpm": bpm,
		"time": 0,
	})

for tm in times:
	notes = noteMap[tm]
	noteList = notes.values()
	hasSim = len(noteList) == 2
	for note in noteList:
		note.generate(resultList, bpm)
		if note.__class__.__name__ == "LineMiddle":
			hasSim = False
	# 是否有同时点击线
	if hasSim:
		resultList.append({
			"type": "Sim",
			"lane": [noteList[0].line, noteList[1].line],
			"time": calcTime(tm, bpm),
		})
		
import json
with open("1.expert.json", "w") as output:
	json.dump(resultList, output)


