# coding: UTF-8

import sys
import math
import json
import codecs
import xml.dom.minidom

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

# 全局数据：
validSongIDList = []
songID2Jacket = {}
bpmInfo = {}

def loadValidSongIDList():
	if len(validSongIDList) != 0:
		return
	# 读取原始songlist，找到可用的songID、和jacketImage，构建可用ID列表：
	with codecs.open("orig/all.5.json", 'r', 'utf-8') as songListFile:
		origSongs = json.load(songListFile)
	
	songIDList = sorted([int(songID) for songID in origSongs.keys()])
	jackets = set()
	for songID in songIDList:
		songInfo = origSongs[str(songID)]
		jacket = songInfo["jacketImage"][0]
		if jacket not in jackets:
			songID2Jacket[songID] = jacket
			validSongIDList.append(songID)
			jackets.add(jacket)

def getSingleMapMetaInfo(mapName):
	configFilePath = "custom/{}/{}.json".format(mapName, mapName)
	config = {}
	with codecs.open(configFilePath, 'r', 'utf-8') as configFile:
		config = json.load(configFile)
	return config

def processMusicMetaInfo():
	loadValidSongIDList()
	
	# 读取custom/maplist.dat：
	mapListFilePath = "custom/maplist.json"
	mapList = []
	with codecs.open(mapListFilePath, 'r', 'utf-8') as mapListFile:
		mapList = json.load(mapListFile)
	mapData = [getSingleMapMetaInfo(mapName) for mapName in mapList]
	
	songs = {}
	singers = {}
	for index, mapInfo in enumerate(mapData):
		singerIndex = index + 1
		singers[str(singerIndex)] = {
			"bandName": [mapInfo["singer"]] * 4,
		}
		songIndex = validSongIDList[index]
		songs[str(songIndex)] = {
			"bandId": singerIndex,
			"musicTitle": [mapInfo["name"]] * 4,
			"difficulty": {
				"3": {
					"playLevel": int(mapInfo["difficulty"]),
				}
			},
			"tag": "normal",
			"publishedAt": ["1462071600000", "1462104000000", "1462075200000", "1462075200000"],
			"jacketImage": [songID2Jacket[validSongIDList[index]]],
		}
	
	with codecs.open("all/all.5.json", "w", 'utf-8') as output:
		json.dump(songs, output, ensure_ascii=False)
		
	with codecs.open("all/all.1.json", "w", 'utf-8') as output:
		json.dump(singers, output, ensure_ascii=False)
		
	# 拷贝每张图片到musicjacket文件夹下：
	for index, mapName in enumerate(mapList):
		jacketPath = "custom/{}/{}.png".format(mapName, mapName)
		jacketNewName = songID2Jacket[validSongIDList[index]]
		targetPath = "musicjacket/{}.png".format(jacketNewName)
		with open(jacketPath, "rb") as source:
			with open(targetPath, "wb") as target:
				target.write(source.read())

# 命令行参数：文件夹名称 是否导出MP3
def processMusics(directoryName, outputMP3):
	directories = {}
	mapListFilePath = "custom/maplist.json"
	mapList = []
	with codecs.open(mapListFilePath, 'r', 'utf-8') as mapListFile:
		mapList = json.load(mapListFile)
		
	loadValidSongIDList()
	
	for index, mapName in enumerate(mapList):
		songIndex = validSongIDList[index]
		if directoryName == "ALL" or mapName == directoryName:
			directories[songIndex] = mapName
	
	for key, value in directories.iteritems():
		process(key, value, outputMP3)
		bpmInfo.clear()
	
	
def process(musicIndex, directoryName, outputMP3):
	print "======Process map:", directoryName
	config = getSingleMapMetaInfo(directoryName)

	# 记录技能节点位置与fever位置：
	skills = []
	fevers = []
	for skill in config.get("skills", []):
		skillPos = str(skill[0])
		skillLine = skill[1]
		skills.append((skillPos, skillLine))
	for fever in config.get("fevers", []):
		fevers.append(str(fever))
	
	# 读取sav文件：
	document = xml.dom.minidom.parse("custom/{}/{}.sav".format(directoryName, directoryName))
	root = document.documentElement
	types = ["N", "L", "F"]

	noteMap = {}
	lineSList = []
	lineMEFList = []

	info = root.getElementsByTagName("info")[0]
	bpm = int(info.getElementsByTagName("bpm")[0].childNodes[0].data)
	delay = config.get("delay", 0) #delay是歌曲开始播放到谱面第0拍开始之间的秒数，和sav文件里的delay不同。
	preLength = config.get("preLength", 8) #preLength是往谱面第0拍前添加的空白的1/8拍的数量。
	bpmInfo["preLength"] = preLength
	bpmInfo["bpm"] = bpm

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
			print "Cannot change {} note to skill note. {} {}".format(noteInst.__class__.__name__, skillPos, skillLine)
		else:
			noteInst.setToSkill()
			
	# 添加fever信息：
	for index, fever in enumerate(fevers):
		if index == 0:
			flag = "FeverReady"
		elif index == 1:
			flag = "FeverStart"
		else:
			flag = "FeverEnd"
		noteMap.setdefault(fever, {})
		noteMap[fever][-1] = flag
	
	# 计算要添加多长时间的空白：、
	length = 60.0 / (bpm * 2) * preLength - delay
	length = max(0, length)
	
	# 打开MP3文件，生成新的MP3文件：
	if outputMP3:
		from pydub import AudioSegment
		music = AudioSegment.from_file("custom/{}/{}.mp3".format(directoryName, directoryName))
		blank = AudioSegment.silent(duration=int(length * 1000))
		resMusic = blank + music
		resMusic.export("music/bgm%03d.mp3" % musicIndex, format="mp3")

	#开始生成json：
	resultListMap = []
	resultListMap.append({
		"type": "BPM",
		"bpm": bpm,
		"time": 0,
	})
	resultListSimulator = []
	times = noteMap.keys()
	times.sort(key=lambda item: float(item))
	
	for tm in times:
		notes = noteMap[tm]
		# fever标记：
		if notes.has_key(-1):
			flag = notes[-1]
			resultListMap.append({
				"type": flag,
				"time": calcTime(tm),
			})
			notes.pop(-1)
		# 其余note输出：
		noteList = notes.values()
		hasSim = len(noteList) == 2
		for note in noteList:
			note.generate(resultListMap)
			note.generate(resultListSimulator)
			if note.__class__.__name__ == "LineMiddle":
				hasSim = False
		# 是否有同时点击线
		if hasSim:
			simDict = {
				"type": "Sim",
				"lane": [noteList[0].line, noteList[1].line],
				"time": calcTime(tm),
			}		
			resultListMap.append(simDict)
			resultListSimulator.append(simDict)
	
	with open("graphics/simulator/{}.expert.json".format(musicIndex), "wt") as output:
		json.dump(resultListSimulator, output)
	with open("graphics/chart/{}.expert.json".format(musicIndex), "wt") as output:
		json.dump(resultListMap, output)

if __name__ == "__main__":
	if sys.argv[1] == "songList":
		processMusicMetaInfo()
	elif sys.argv[1] == "song":
		directoryName = sys.argv[2]
		outputMP3 = sys.argv[3] == "1" if len(sys.argv) >= 4 else False
		processMusics(directoryName, outputMP3)
