# coding: UTF-8

import sys
import math
import json
import xml.dom.minidom
from pydub import AudioSegment

def calcTime(pos):
	bpm = bpmInfo["bpm"]
	preLength = bpmInfo["preLength"]
	return 60.0 / (bpm * 2) * (float(pos) + preLength)
	
def isGrayNote(pos):
	return '.' in pos

class NoteBase(object):
	def __init__(self, note, tp):
		self.line = int(note.getElementsByTagName('line{}'.format(tp))[0].childNodes[0].data) + 4
		self.pos = str(note.getElementsByTagName('pos{}'.format(tp))[0].childNodes[0].data)
		
	def generate(self, resultList, bpm):
		pass

# 单键，包括蓝键和灰键
# line: 1-7
# pos: 节拍数
class NoteN(NoteBase):
	def __init__(self, note, tp):
		super(NoteN, self).__init__(note, tp)
		self.isSkill = False
		
	def generate(self, resultList):
		resultList.append({
			"type": "Skill" if self.isSkill else ("SingleOff" if isGrayNote(self.pos) else "Single"),
			"lane": self.line,
			"time": calcTime(self.pos),
		})
		
	def setToSkill(self):
		self.isSkill = True

# 粉键
class NoteF(NoteBase):
	def __init__(self, note, tp):
		super(NoteF, self).__init__(note, tp)
		
	def generate(self, resultList):
		resultList.append({
			"type": "Flick",
			"lane": self.line,
			"time": calcTime(self.pos),
		})

# 滑条起点
# nextNote可以是LineMiddle，LineEndN和LineEndF
class LineStart(NoteBase):
	def __init__(self, note, tp):
		super(LineStart, self).__init__(note, tp)
		self.lineInsts = []
		self.nextNode = None
		self.prevNode = None
		self.isSkill = False
		
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
			"type": "Skill" if self.isSkill else "Long",
			"lane": self.line,
			"time": calcTime(self.pos),
		})
		resultList.append({
			"type": "Bar",
			"lane": [self.line, self.nextNode.line],
			"time": [calcTime(self.pos), calcTime(self.nextNode.pos)],
		})
		
	def setToSkill(self):
		self.isSkill = True

# 滑条中间节点
class LineMiddle(NoteBase):
	def __init__(self, note, tp):
		super(LineMiddle, self).__init__(note, tp)
		self.startLine = int(note.getElementsByTagName('startlineL'.format(tp))[0].childNodes[0].data) + 4
		self.startPos = str(note.getElementsByTagName('startposL'.format(tp))[0].childNodes[0].data)
		self.nextNode = None
		self.prevNode = None
		
	def generate(self, resultList):
		resultList.append({
			"type": "Tick",
			"lane": self.line,
			"time": calcTime(self.pos),
		})
		resultList.append({
			"type": "Bar",
			"lane": [self.line, self.nextNode.line],
			"time": [calcTime(self.pos), calcTime(self.nextNode.pos)],
		})

# 滑条终点N
class LineEndN(NoteBase):
	def __init__(self, note, tp):
		super(LineEndN, self).__init__(note, tp)
		self.startLine = int(note.getElementsByTagName('startlineL'.format(tp))[0].childNodes[0].data) + 4
		self.startPos = str(note.getElementsByTagName('startposL'.format(tp))[0].childNodes[0].data)
		self.nextNode = None
		self.prevNode = None
		
	def generate(self, resultList):
		resultList.append({
			"type": "Long",
			"lane": self.line,
			"time": calcTime(self.pos),
		})

# 滑条终点F
class LineEndF(NoteBase):
	def __init__(self, note, tp):
		super(LineEndF, self).__init__(note, tp)
		self.startLine = int(note.getElementsByTagName('startlineL'.format(tp))[0].childNodes[0].data) + 4
		self.startPos = str(note.getElementsByTagName('startposL'.format(tp))[0].childNodes[0].data)
		self.nextNode = None
		self.prevNode = None
		
	def generate(self, resultList):
		resultList.append({
			"type": "Flick",
			"lane": self.line,
			"time": calcTime(self.pos),
		})

nodeTypeClsDict = {
	"N": NoteN,
	"F": NoteF,
	"LS": LineStart,
	"LM": LineMiddle,
	"LE": LineEndN,
	"LF": LineEndF,
}

bpmInfo = {}

# 支持的命令行参数：
# -sav super.sav 输入的sav文件名；
# -map 导出map谱面；
# -simulator 导出simulator谱面；
# -mp3 super.mp3 输入的mp3文件名
# -preLength 16 在谱面开始前添加的空白长度（以1/8拍的整数倍计算，若此参数值为16，则表明在谱面开始前添加16个1/8拍的长度）
#		*谱面开始前：从sav文件的delay表示的时间开始，若delay为0.063，则表示从原音频的63ms处谱面开始，此时在音频前添加的空白长度为16个1/8拍的长度减去63ms
# -json 1.expert.json 输出的json文件名
# -outmp3 bgm001.mp3 输出的mp3文件名
# -skill 32,2,128,4,224,4,320,6 技能节点，最多六个
def process():
	argvDict = {}
	index = 1
	skills = []
	while index < len(sys.argv):
		currArg = sys.argv[index]
		if currArg == "-sav":
			argvDict["sav"] = sys.argv[index + 1]
			index += 1
		elif currArg == "-mp3":
			argvDict["mp3"] = sys.argv[index + 1]
			index += 1
		elif currArg == "-preLength":
			argvDict["preLength"] = int(sys.argv[index + 1])
			index += 1
		elif currArg == "-json":
			argvDict["json"] = sys.argv[index + 1]
			index += 1
		elif currArg == "-outmp3":
			argvDict["outmp3"] = sys.argv[index + 1]
			index += 1
		elif currArg == "-map":
			argvDict["map"] = True
		elif currArg == "-simulator":
			argvDict["simulator"] = True
		elif currArg == "-skill":
			skillStr = sys.argv[index + 1]
			index += 1
			# 处理skillStr
			skillStrList = skillStr.split(",")
			for i in xrange(len(skillStrList)):
				if i % 2 == 1:
					continue
				skillPos = skillStrList[i]
				skillLine = int(skillStrList[i + 1])
				skills.append((skillPos, skillLine))
			
		index += 1
	
	if "sav" not in argvDict:
		print "No input sav file path."
		return

	document = xml.dom.minidom.parse(argvDict["sav"])
	root = document.documentElement
	types = ["N", "L", "F"]

	noteMap = {}
	lineSList = []
	lineMEFList = []

	info = root.getElementsByTagName("info")[0]
	bpm = int(info.getElementsByTagName("bpm")[0].childNodes[0].data)
	bpmInfo["bpm"] = bpm
	delay = float(info.getElementsByTagName("delay")[0].childNodes[0].data)

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

	# 添加skill节点：
	for skillPos, skillLine in skills:
		noteInst = noteMap.get(skillPos, {}).get(skillLine)
		if noteInst is None:
			print "No note at {}, {}".format(skillPos, skillLine)
		elif noteInst.__class__.__name__ not in ["LineStart", "NoteN"]:
			print "Cannot change {} note to skill note.".format(noteInst.__class__.__name__)
		else:
			noteInst.setToSkill()
	
	# 计算要添加多长时间的空白：
	preLength = 0
	length = 0
	valid = False
	if "preLength" in argvDict:
		preLength = argvDict["preLength"]
		length = 60.0 / (bpm * 2) * (preLength - 1) # 虽然不知道为什么，但是这里好像要减去1/8拍？暂时存疑，看看这个方法是不是每首歌都适用。
		if length >= delay:
			valid = True
	
	if not valid:
		# 需要自动算出preLength：
		preLengthFloat = delay / (60.0 / (bpm * 2)) / 8
		preLengthFloat = math.ceil(preLengthFloat)
		preLength = int(preLengthFloat) * 8
		length = 60.0 / (bpm * 2) * (preLength - 1) # 虽然不知道为什么，但是这里好像要减去1/8拍？暂时存疑，看看这个方法是不是每首歌都适用。
		
	bpmInfo["preLength"] = preLength
	
	# 打开MP3文件，生成新的MP3文件：
	if "mp3" in argvDict:
		music = AudioSegment.from_file(argvDict["mp3"])
		blank = AudioSegment.silent(duration=int((length - delay) * 1000))
		resMusic = blank + music
		resMusic.export("music/{}".format(argvDict.get("outmp3", "bgm001.mp3")), format="mp3")

	#开始生成json：
	resultList = []
	times = noteMap.keys()
	times.sort(key=lambda item: float(item))
	
	for tm in times:
		notes = noteMap[tm]
		noteList = notes.values()
		hasSim = len(noteList) == 2
		for note in noteList:
			note.generate(resultList)
			if note.__class__.__name__ == "LineMiddle":
				hasSim = False
		# 是否有同时点击线
		if hasSim:
			resultList.append({
				"type": "Sim",
				"lane": [noteList[0].line, noteList[1].line],
				"time": calcTime(tm),
			})
	
	if "simulator" in argvDict:
		with open("graphics/simulator/{}".format(argvDict.get("json", "1.expert.json")), "wt") as output:
			json.dump(resultList, output)
	if "map" in argvDict:
		resultList.insert(0, {
			"type": "BPM",
			"bpm": bpm,
			"time": 0,
		})
		with open("graphics/chart/{}".format(argvDict.get("json", "1.expert.json")), "wt") as output:
			json.dump(resultList, output)

if __name__ == "__main__":
	process()
