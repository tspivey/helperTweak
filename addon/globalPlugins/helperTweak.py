import NVDAHelper
from ctypes import *
from winAPI.constants import SystemErrorCodes
import queueHandler
import api
import buildVersion
import config
import globalPluginHandler

@WINFUNCTYPE(c_long,c_wchar_p)
def nvdaController_speakText(text):
	focus=api.getFocusObject()
	if focus.sleepMode==focus.SLEEP_FULL:
		return -1
	import speech
	queueHandler.queueFunction(queueHandler.eventQueue,speech.speakText,text, _immediate=True)
	return SystemErrorCodes.SUCCESS

@WINFUNCTYPE(c_long, c_wchar_p, c_wchar_p)
def nvdaControllerInternal_reportLiveRegion(text: str, politeness: str):
	assert isinstance(text, str), "Text isn't a string"
	assert isinstance(politeness, str), "Politeness isn't a string"
	if not config.conf["presentation"]["reportDynamicContentChanges"]:
		return -1
	focus = api.getFocusObject()
	if focus.sleepMode == focus.SLEEP_FULL:
		return -1
	import speech
	import braille
	from aria import AriaLivePoliteness
	from speech.priorities import Spri

	try:
		politenessValue = AriaLivePoliteness(politeness.lower())
	except ValueError:
		log.error(
			f"nvdaControllerInternal_reportLiveRegion got unknown politeness of {politeness}",
			exc_info=True,
		)
		return -1
	if politenessValue == AriaLivePoliteness.OFF:
		log.error(f"nvdaControllerInternal_reportLiveRegion got unexpected politeness of {politeness}")
	if politenessValue  == AriaLivePoliteness.ASSERTIVE:
		queueHandler.queueFunction(queueHandler.eventQueue, speech.cancelSpeech)
	queueHandler.queueFunction(
		queueHandler.eventQueue,
		speech.speakText,
		text,
		priority=(Spri.NEXT if politenessValue == AriaLivePoliteness.ASSERTIVE else Spri.NORMAL),
		_immediate=True,
	)
	queueHandler.queueFunction(
		queueHandler.eventQueue,
		braille.handler.message,
		text,
	)
	return 0

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super().__init__()
		if buildVersion.version_year < 2026:
			self.dll = NVDAHelper.localLib
		else:
			self.dll = NVDAHelper.localLib.dll
		NVDAHelper._setDllFuncPointer(self.dll, "_nvdaController_speakText", nvdaController_speakText)
		NVDAHelper._setDllFuncPointer(self.dll, "_nvdaControllerInternal_reportLiveRegion", nvdaControllerInternal_reportLiveRegion)

	def terminate(self):
		NVDAHelper._setDllFuncPointer(self.dll, "_nvdaController_speakText", NVDAHelper.nvdaController_speakText)
		NVDAHelper._setDllFuncPointer(self.dll, "_nvdaControllerInternal_reportLiveRegion", NVDAHelper.nvdaControllerInternal_reportLiveRegion)
