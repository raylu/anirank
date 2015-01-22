import datetime
import http.client
from xml.etree import ElementTree

def animelist(username):
	conn = http.client.HTTPConnection('myanimelist.net')
	headers = {'User-Agent': 'api-taiga-32864c09ef538453b4d8110734ee355b'}
	conn.request('GET', '/malappinfo.php?u=raylu&status=all&type=anime', headers=headers)
	response = conn.getresponse()
	if response.status != http.client.OK:
		raise http.client.HTTPException()
	xml = ElementTree.parse(response)
	for anime in xml.getroot().iter('anime'):
		entry = {}
		for el in anime:
			entry[el.tag] = el.text
		yield parse_entry(entry)

types = ['TV', 'OVA', 'movie', 'special', 'ONA', 'music']
anime_status = ['airing', 'finished', 'not yet aired']
animelist_status = {'1': 'watching', '2': 'completed', '3': 'on hold', '4': 'dropped', '6': 'plan to watch'}
def parse_entry(entry):
	synonyms = entry['series_synonyms']
	if synonyms is not None:
		synonyms = synonyms.split('; ')
		if not synonyms[0]:
			synonyms = synonyms[1:]
	anime = {
		'id': int(entry['series_animedb_id']),
		'title': entry['series_title'],
		'synonyms': synonyms,
		'type': types[int(entry['series_type']) - 1],
		'status': anime_status[int(entry['series_status']) - 1],
		'start': datetime.datetime.strptime(entry['series_start'], '%Y-%m-%d').date(),
		'end': datetime.datetime.strptime(entry['series_end'], '%Y-%m-%d').date(),
		'episodes': int(entry['series_episodes']),
		'image': entry['series_image'],
	}
	user_status = {
		'status': animelist_status[entry['my_status']],
		'episodes': int(entry['my_watched_episodes']),
		'mal_score': int(entry['my_score']),
		'last_updated': datetime.datetime.utcfromtimestamp(int(entry['my_last_updated'])),
	}
	return anime, user_status

if __name__ == '__main__':
	import sys
	from pprint import pprint
	pprint(list(animelist(sys.argv[1])))
