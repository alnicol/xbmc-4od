#/bin/python
# -*- coding: utf-8 -*-

import os
import xbmcplugin
import xbmcgui
import re
import geturllib
import fourOD_token_decoder
import mycgi

gPluginName  = 'plugin.video.4od'
gPluginHandle = int(sys.argv[1])
gBaseURL = sys.argv[0]


#==============================================================================
# ShowCategories
#
# List the programme categories, retaining the 4oD order
#==============================================================================

def ShowCategories():
	html = geturllib.GetURL( "http://www.channel4.com/programmes/tags/4od", 200000 ) # ~2 days
	html = re.findall( '<ol class="display-cats">(.*?)</div>', html, re.DOTALL )[0]
	categories = re.findall( '<a href="/programmes/tags/(.*?)/4od">(.*?)</a>', html, re.DOTALL )
	
	listItems = []
	# Start with a Search entry
	newListItem = xbmcgui.ListItem( "Search" )
	url = gBaseURL + '?search=1'
	listItems.append( (url,newListItem,True) )
	for categoryInfo in categories:
		label = remove_extra_spaces(remove_html_tags(categoryInfo[1]))
		newListItem = xbmcgui.ListItem( label=label )
		url = gBaseURL + '?category=' + mycgi.URLEscape(categoryInfo[0]) + '&title=' + mycgi.URLEscape(label)
		listItems.append( (url,newListItem,True) )
	xbmcplugin.addDirectoryItems( handle=gPluginHandle, items=listItems )
	xbmcplugin.endOfDirectory( handle=gPluginHandle, succeeded=True )
		

#==============================================================================

def ShowCategory( category ):
	pg = 1
	count = 50
	listItems = []
	while (count == 50):
		html = geturllib.GetURL( "http://www.channel4.com/programmes/tags/%s/4od/title/brand-list/page-%s" % (category,pg), 40000 ) # ~12 hrs
		showsInfo = re.findall( '<li.*?<a class=".*?" href="/programmes/(.*?)/4od".*?<img src="(.*?)".*?<p class="title">(.*?)</p>.*?<p class="synopsis">(.*?)</p>', html, re.DOTALL )
		
		count = 0
		for showInfo in showsInfo:
			count = count + 1
			showId = showInfo[0]
			thumbnail = "http://www.channel4.com" + showInfo[1]
			progTitle = showInfo[2]
			progTitle = progTitle.replace( '&amp;', '&' )
			synopsis = showInfo[3].strip()
			synopsis = synopsis.replace( '&amp;', '&' )
			synopsis = synopsis.replace( '&pound;', '£' )
			
			newListItem = xbmcgui.ListItem( progTitle )
			newListItem.setThumbnailImage(thumbnail)
			newListItem.setInfo('video', {'Title': progTitle, 'Plot': synopsis, 'PlotOutline': synopsis})
			url = gBaseURL + '?category=' + category + '&show=' + mycgi.URLEscape(showId) + '&title=' + mycgi.URLEscape(progTitle)
			listItems.append( (url,newListItem,True) )
		pg = pg + 1
	
	xbmcplugin.addDirectoryItems( handle=gPluginHandle, items=listItems )
	xbmcplugin.setContent(handle=gPluginHandle, content='tvshows')
	xbmcplugin.endOfDirectory( handle=gPluginHandle, succeeded=True )

#==============================================================================

def ShowEpisodes( showId, showTitle ):
	html = geturllib.GetURL( "http://www.channel4.com/programmes/" + showId + "/4od", 20000 ) # ~6 hrs
	genre = re.search( '<meta name="primaryBrandCategory" content="(.*?)"/>', html, re.DOTALL ).groups()[0]
	ol = re.search( '<ol class="all-series">(.*?)</div>', html, re.DOTALL ).groups()[0]
	epsInfo = re.findall( '<li.*?data-episode-number="(.*?)".*?data-assetid="(.*?)".*?data-episodeUrl="(.*?)".*?data-image-url="(.*?)".*?data-txDate="(.*?)".*?data-episodeTitle="(.*?)".*?data-episodeInfo="(.*?)".*?data-episodeSynopsis="(.*?)".*?data-series-number="(.*?)"', ol, re.DOTALL )
	
	listItems = []
	epsDict = dict()
	for epInfo in epsInfo:
		epNum = epInfo[0]
		try: epNumInt = int(epNum)
		except: epNumInt = ""
		premieredDate = epInfo[4]
		seriesNum = epInfo[8]
		if ( seriesNum <> "" and epNum <> "" ):
			fn = showId + ".s%0.2ie%0.2i" % (int(seriesNum),int(epNum))
		else:
			fn = showId
		id = epInfo[1]
		
		if ( not id in epsDict ):
			epsDict[id] = 1
			
			img = epInfo[3]
			progTitle = epInfo[5].strip()
			progTitle = progTitle.replace( '&amp;', '&' )
			epTitle = epInfo[6].strip()
			if ( progTitle == showTitle and epTitle <> "" ):
				label = epTitle
			else:
				label = progTitle
			url = "http://www.channel4.com" + epInfo[2]
			description = remove_extra_spaces(remove_html_tags(epInfo[7]))
			description = description.replace( '&amp;', '&' )
			description = description.replace( '&pound;', '£' )
			description = description.replace( '&quot;', "'" )
			if (img == ""):
				thumbnail = re.search( '<meta property="og:image" content="(.*?)"', html, re.DOTALL ).groups()[0]
			else:
				thumbnail = "http://www.channel4.com" + img
			
			newListItem = xbmcgui.ListItem( label )
			newListItem.setThumbnailImage(thumbnail)
			newListItem.setInfo('video', {'Title': label, 'Plot': description, 'PlotOutline': description, 'Genre': genre, 'premiered': premieredDate, 'Episode': epNumInt})
			url = gBaseURL + '?ep=' + mycgi.URLEscape(id) + "&title=" + mycgi.URLEscape(label) + "&fn=" + mycgi.URLEscape(fn)
			listItems.append( (url,newListItem,False) )
	
	xbmcplugin.addDirectoryItems( handle=gPluginHandle, items=listItems )
	xbmcplugin.setContent(handle=gPluginHandle, content='episodes')
	xbmcplugin.endOfDirectory( handle=gPluginHandle, succeeded=True )

#==============================================================================


def PlayOrDownloadEpisode( episodeId, title, defFilename='' ):
	import xbmcaddon
	addon = xbmcaddon.Addon(id=gPluginName)
	action = addon.getSetting( 'select_action' )
	if ( action == 'Ask' ):
		dialog = xbmcgui.Dialog()
		ret = dialog.yesno(title, 'Do you want to play or download?', '', '', 'Download',  'Play') # 1=Play; 0=Download
	elif ( action == 'Downlad' ):
		ret = 0
	else:
		ret = 1
	
	# Get the stream info
	xml = geturllib.GetURL( "http://ais.channel4.com/asset/%s" % episodeId, 0 )
	uriData = re.search( '<uriData>(.*?)</uriData>', xml, re.DOTALL).groups()[0]
	streamUri = re.search( '<streamUri>(.*?)</streamUri>', uriData, re.DOTALL).groups()[0]
	token = re.search( '<token>(.*?)</token>', uriData, re.DOTALL).groups()[0]
	cdn = re.search( '<cdn>(.*?)</cdn>', uriData, re.DOTALL).groups()[0]
	decodedToken = fourOD_token_decoder.Decode4odToken(token)
	if ( cdn ==  "ll" ):
		ip = re.search( '<ip>(.*?)</ip>', uriData, re.DOTALL ).groups()[0]
		e = re.search( '<e>(.*?)</e>', uriData, re.DOTALL ).groups()[0]
		auth = "e=%s&ip=%s&h=%s" % (e,ip,decodedToken)
	else:
		fingerprint = re.search( '<fingerprint>(.*?)</fingerprint>', uriData, re.DOTALL ).groups()[0]
		slist = re.search( '<slist>(.*?)</slist>', uriData, re.DOTALL ).groups()[0]
		auth = "auth=%s&aifp=%s&slist=%s" % (decodedToken,fingerprint,slist)
	
	if ( ret == 1 ):
		# Play
		url = re.findall( '(.*?)mp4:', streamUri, re.DOTALL )[0]
		url = url.replace( '.com/', '.com:1935/' )
		playpath = re.search( '(mp4:.*)', streamUri, re.DOTALL ).groups()[0]
		playpath = playpath + '?' + auth
		swfplayer = "http://www.channel4.com/static/programmes/asset/flash/swf/4odplayer-11.8.5.swf"
		playURL = "%s?ovpfv=1.1&%s playpath=%s swfurl=%s swfvfy=true" % (url,auth,playpath,swfplayer)
		
		li = xbmcgui.ListItem(title)
		li.setInfo('video', {'Title': title})
		xbmc.Player().play( playURL, li )
	else:
		# Download
		# Ensure rtmpdump has been located
		rtmpdump_path = addon.getSetting('rtmpdump_path')
		if ( rtmpdump_path is '' ):
			d = xbmcgui.Dialog()
			d.ok('Download Error','You have not located your rtmpdump executable.\n Please update the addon settings and try again.','','')
			addon.openSettings(sys.argv[ 0 ])
			return
			
		# Ensure default download folder is defined
		downloadFolder = addon.getSetting('download_folder')
		if downloadFolder is '':
			d = xbmcgui.Dialog()
			d.ok('Download Error','You have not set the default download folder.\n Please update the addon settings and try again.','','')
			addon.openSettings(sys.argv[ 0 ])
			return
			
		if ( addon.getSetting('ask_filename') == 'true' ):
			kb = xbmc.Keyboard( defFilename, 'Save programme as...' )
			kb.doModal()
			if (kb.isConfirmed()):
				filename = kb.getText()
			else:
				return
		else:
			filename = defFilename
		
		if ( filename.endswith('.flv') == False ): 
			filename = filename + '.flv'
		
		if ( addon.getSetting('ask_folder') == 'true' ):
			dialog = xbmcgui.Dialog()
			downloadFolder = dialog.browse(  3, 'Save to folder...', 'files', '', False, False, downloadFolder )
			if ( downloadFolder == '' ):
				return
				
		savePath = os.path.join( "T:"+os.sep, downloadFolder, filename )
		from subprocess import Popen, PIPE, STDOUT
		
		cmdline = CreateRTMPDUMPCmd( rtmpdump_path, streamUri, auth, savePath ) 
		xbmc.executebuiltin('XBMC.Notification(4oD,Starting download: %s)' % filename)
		p = Popen( cmdline, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT )
		x = p.stdout.read()
		import time 
		while p.poll() == None:
			time.sleep(2)
			x = p.stdout.read()
			
		xbmc.executebuiltin("XBMC.Notification(Download Finished!,"+filename+",2000)")
	
	return

#==============================================================================

def CreateRTMPDUMPCmd( rtmpdump_path, streamUri, auth, savePath ):
	
	#rtmpdump
	#-r "rtmpe://ak.securestream.channel4.com:1935/4oD/?ovpfv=1.1&auth=da_ana4cDc3d_d4dtaPd0clcndUa3claHcG-boODFj-eS-gxS-s8p4mbq4tRlim9lSmdpcp6l1nb&aifp=v002&slist=assets/CH4_08_02_900_47548001001002_005.mp4"
	#-a "4oD/?ovpfv=1.1&auth=da_ana4cDc3d_d4dtaPd0clcndUa3claHcG-boODFj-eS-gxS-s8p4mbq4tRlim9lSmdpcp6l1nb&aifp=v002&slist=assets/CH4_08_02_900_47548001001002_005.mp4"
	#-f "WIN 11,0,1,152"
	#-W "http://www.channel4.com/static/programmes/asset/flash/swf/4odplayer-11.8.5.swf"
	#-p "http://www.channel4.com/programmes/peep-show/4od/player/3156662"
	#-C Z:
	#-y "mp4:assets/CH4_08_02_900_47548001001002_005.mp4"
	#-o CH4_08_02_900_47548001001002_005.flv
	
	rtmpUrl = re.search( '(.*?)mp4:', streamUri, re.DOTALL ).groups()[0]
	rtmpUrl = rtmpUrl.replace( '.com/', '.com:1935/' )
	rtmpUrl = rtmpUrl + "?ovpfv=1.1&" + auth
	app = re.search( '.com/(.*?)mp4:', streamUri, re.DOTALL ).groups()[0]
	app = app + "?ovpfv=1.1&" + auth
	#swfplayer = "http://www.channel4.com/static/programmes/asset/flash/swf/4odplayer-11.8.swf"
	swfplayer = "http://www.channel4.com/static/programmes/asset/flash/swf/4odplayer-11.8.5.swf"
	playpath = re.search( '.*?(mp4:.*)', streamUri, re.DOTALL ).groups()[0]
	playpath = playpath + "?" + auth
	args = [
				rtmpdump_path,
				"--rtmp", '"%s"' % rtmpUrl,
				"--app", '"%s"' % app,
				#"--flashVer", '"WIN 10,3,183,7"',
				"--flashVer", '"WIN 11,0,1,152"',
				"--swfVfy", '"%s"' % swfplayer,
				#"--pageUrl xxxxxx",
				"--conn", "Z:",
				"--playpath", '"%s"'%playpath,
				"-o", '"%s"' % savePath,
				"--verbose"
				]
	cmdline = ' '.join(args)
		
	return cmdline
	
#==============================================================================

def DoSearch():
	kb = xbmc.Keyboard( "", 'Search' )
	kb.doModal()
	if ( kb.isConfirmed() == False ): return
	query = kb.getText()
	DoSearchQuery( query )

def DoSearchQuery( query ):
	data = geturllib.GetURL( "http://www.channel4.com/search/predictive/?q=%s" % mycgi.URLEscape(query), 10000 )
	infos = re.findall( '{"imgUrl":"(.*?)".*?"value": "(.*?)".*?"siteUrl":"(.*?)","fourOnDemand":"true"}', data, re.DOTALL )
	listItems = []
	for info in infos:
		img = info[0]
		title = info[1]
		progUrl  = info[2]
		
		title = title.replace( '&amp;', '&' )
		title = title.replace( '&pound;', '£' )
		title = title.replace( '&quot;', "'" )
		
		img = "http://www.channel4.com" + img
		showId = re.search( 'programmes/(.*?)/4od', progUrl, re.DOTALL ).groups()[0]
		newListItem = xbmcgui.ListItem( title )
		newListItem.setThumbnailImage(img)
		url = gBaseURL + '?show=' + mycgi.URLEscape(showId) + '&title=' + mycgi.URLEscape(title)
		listItems.append( (url,newListItem,True) )
	xbmcplugin.addDirectoryItems( handle=gPluginHandle, items=listItems )
	xbmcplugin.setContent(handle=gPluginHandle, content='tvshows')
	xbmcplugin.endOfDirectory( handle=gPluginHandle, succeeded=True )
                                      

#==============================================================================


def remove_html_tags(data):
    p = re.compile(r'<.*?>')
    return p.sub('', data)

def remove_extra_spaces(data):
    p = re.compile(r'\s+')
    return p.sub(' ', data)
   
if __name__ == "__main__":
	try:
		geturllib.SetCacheDir( xbmc.translatePath(os.path.join( "T:"+os.sep,"addon_data", gPluginName,'cache' )) )
		
		if ( mycgi.EmptyQS() ):
			ShowCategories()
		else:
			(category, showId, episodeId, title, search) = mycgi.Params( 'category', 'show', 'ep', 'title', 'search' )
			if ( search <> '' ):
				DoSearch()
			elif ( showId <> '' ):
				ShowEpisodes( showId, title )
			elif ( category <> '' ):
				ShowCategory( category )
			elif ( episodeId <> '' ):
				PlayOrDownloadEpisode( episodeId, title, mycgi.Param('fn') )
	except:
		# Make sure the text from any script errors are logged
		import traceback
		traceback.print_exc(file=sys.stdout)
		raise