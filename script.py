import podcastparser
import xml.etree.ElementTree as ET
import urllib.request
import pprint
from xml.dom import minidom
import requests
import re
import time
import json

def ajouter_zeros(nombre):
    # Convertir le nombre en chaîne de caractères
    nombre_str = str(nombre)
    # Utiliser zfill pour ajouter des zéros devant le nombre
    # jusqu'à ce qu'il ait une longueur de 2 caractères
    return nombre_str.zfill(2)

def extract_number(title):
    """Extract the first number found in the title for sorting."""
    numbers = re.findall(r'\d+', title)
    # pprint.pprint(numbers)
    return int(numbers[0]) if numbers else 0

def prettify(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def download_rss(url, cache_file):
    """Download the RSS feed and cache it locally."""
    response = requests.get(url)
    if response.status_code == 200:
        with open(cache_file, 'wb') as f:
            f.write(response.content)
    else:
        raise Exception(f"Failed to download RSS feed: HTTP {response.status_code}")

def modify_podcast_rss(input_url, cache_file, output_file):
    try:
        # Essayer de lire le contenu mis en cache
        with open(cache_file, 'r') as f:
            rss_content = f.read()
    except FileNotFoundError:
        # Télécharger le contenu si le cache n'existe pas
        print("Downloading RSS feed...")
        download_rss(input_url, cache_file)
        with open(cache_file, 'r') as f:
            rss_content = f.read()
    # Analyser le flux RSS à partir de l'URL
    parsed = podcastparser.parse(input_url, urllib.request.urlopen(input_url))
    with open("yourlogfile.json", "w") as log_file:
        pprint.pprint(parsed, log_file)
    # Créer un nouvel élément RSS
    rss = ET.Element("rss", {
        "xmlns:itunes":"http://www.itunes.com/dtds/podcast-1.0.dtd",
        "xmlns:pa":"http://podcastaddict.com",
        "xmlns:podcastRF":"http://radiofrance.fr/Lancelot/Podcast#",
        "xmlns:googleplay":"http://www.google.com/schemas/play-podcasts/1.0",
        "version":"2.0",
    })
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = 'Uniquement les histoires de Toudou'
    ET.SubElement(channel, "link").text = parsed.get('link', '')
    ET.SubElement(channel, "description").text = parsed.get('description', '')
    ET.SubElement(channel, "language").text = parsed.get('language', '')
    ET.SubElement(channel, "copyright").text = parsed.get('generator', '')
    # ET.SubElement(channel, "lastBuildDate").text = parsed.get('lastBuildDate', '')
    ET.SubElement(channel, "generator").text = parsed.get('generator', '')
    img = ET.SubElement(channel, "image")
    ET.SubElement(img, "url").text = "https://www.radiofrance.fr/s3/cruiser-production-eu3/2022/11/0e9a29ba-7954-47ae-b0c6-b8cb16efdf3d/1400x1400_rf_omm_0000037236_ite.jpg"
    ET.SubElement(img, "title").text = 'Uniquement les histoires de Toudou'
    ET.SubElement(img, "link").text = "https://www.radiofrance.fr/franceinter/podcasts/toudou"
    ET.SubElement(channel, "itunes:author").text = 'France Inter'
    ET.SubElement(channel, "itunes:category", {
        "text": str(parsed.get('itunes_categories', '')[0][0]),
    })
    ET.SubElement(channel, "itunes:explicit").text = 'no'
    ET.SubElement(channel, "itunes:image", {
        "href": "https://www.radiofrance.fr/s3/cruiser-production-eu3/2022/11/0e9a29ba-7954-47ae-b0c6-b8cb16efdf3d/1400x1400_rf_omm_0000037236_ite.jpg",
    })
    owners = ET.SubElement(channel, "itunes:owner")
    ET.SubElement(owners, "itunes:email").text = parsed.get('itunes_owner', '').get('email')
    ET.SubElement(owners, "itunes:name").text = parsed.get('generator', '')
    ET.SubElement(channel, "itunes:subtitle").text = 'Uniquement les histoires de Toudou'
    ET.SubElement(channel, "itunes:summary").text = ''
    ET.SubElement(channel, "itunes:new-feed-url").text = parsed.get('new_url', '')
    ET.SubElement(channel, "pa:new-feed-url").text = parsed.get('new_url', '')
    ET.SubElement(channel, "podcastRF:originStation").text = '1'
    ET.SubElement(channel, "googleplay:block").text = 'yes'
    # Trier les épisodes par titre
    # sorted_episodes = sorted(parsed['episodes'], key=lambda x: x.get('title', ''))
    sorted_episodes = sorted(parsed['episodes'], key=lambda x: extract_number(x.get('title', '')), reverse=True)
    # Ajouter les épisodes triés et modifiés avec un élément file_size conditionnel
    episodes_added_list=set([])
    for episode in sorted_episodes:
        episode_nomber=ajouter_zeros(extract_number(episode.get('title', '')))
        if (episode.get('title', '').startswith("Les histoires de Toudou")) and (episode_nomber not in episodes_added_list) :
            item = ET.SubElement(channel, "item")
            # print(ajouter_zeros(extract_number(episode.get('title', ''))))
            title=f"{episode_nomber}/{episode['title'].replace('Les histoires de Toudou ', '').split('/')[1]}"
            print(episode_nomber)
            # print(episode_nomber not in episodes_added_list)
            episodes_added_list.add(episode_nomber)
            # print(episodes_added_list)
            # print(f"episode_nomber {episode_nomber}")
            # print(f"episode_added {episode_added}")
            # ET.SubElement(item, "title").text = f"Modified: {episode['title'].replace('Les histoires de Toudou ', '')}"
            ET.SubElement(item, "title").text = title
            ET.SubElement(item, "link").text = episode.get('link', '')
            ET.SubElement(item, "description").text = episode.get('description', '')
            ET.SubElement(item, "author").text = parsed.get('itunes_owner', '').get('email')
            ET.SubElement(item, "category").text = str(parsed.get('itunes_categories', '')[0][0])
            # Ajouter un élément enclosure avec l'URL, la taille du fichier et le type MIME
            for enclosure in episode['enclosures']:
               url = enclosure.get('url', '')
               mime_type = enclosure.get('mime_type', '')
               file_size =  str(enclosure.get('file_size', ''))
            ET.SubElement(item, "enclosure", {
                "url": url,
                "length": str(file_size),
                "type": mime_type
            })
            ET.SubElement(item, "guid", {
                "isPermaLink": 'false'
            }).text = episode.get('guid', '')
            ET.SubElement(item, "pubDate").text = time.strftime("%a, %d %b %Y %I:%M:%S +2000", time.gmtime(episode.get('published', '')))
            ET.SubElement(item, "podcastRF:businessReference").text = '49744'
            # ET.SubElement(item, "podcastRF:magnetothequeID").text = url.split('-')[-2]
            # ET.SubElement(item, "podcastRF:magnetothequeID").text = '2025F49744E'
            index = url.find('49744')
            # Extraire la sous-chaîne souhaitée
            if index != -1:
                result = url[index-5:index+10]
                # print(result)
                ET.SubElement(item, "podcastRF:magnetothequeID").text = result
            ET.SubElement(item, "itunes:title").text = title
            ET.SubElement(item, "itunes:image", {
                "href": episode.get('episode_art_url', ''),
            })
            ET.SubElement(item, "itunes:author").text = episode.get('itunes_author', '')
            ET.SubElement(item, "itunes:keywords").text = title
            ET.SubElement(item, "itunes:category", {
                "text": str(parsed.get('generator', '')),
            })
            ET.SubElement(item, "itunes:owner", {
                "href": episode.get('episode_art_url', ''),
            })
            ET.SubElement(item, "itunes:subtitle").text = title
            ET.SubElement(item, "itunes:summary").text = episode.get('description', '')
            ET.SubElement(item, "itunes:duration").text = time.strftime('%H:%M:%S', time.gmtime(episode.get('total_time', ''))) 
            ET.SubElement(item, "googleplay:block").text = 'yes'
    # Créer un arbre XML et l'écrire dans un fichier
    tree = ET.ElementTree(rss)
    tree.write(output_file, encoding='utf-8', xml_declaration=True)
    # # Utiliser minidom pour formater le XML avec indentation
    # pretty_xml = prettify(rss)
    # # Écrire le XML formaté dans un fichier
    # with open(output_file, "w") as f:
    #     f.write(pretty_xml)

# Exemple d'utilisation
input_url = "https://radiofrance-podcast.net/podcast09/rss_23713.xml"
cache_file = "podcast_cache.xml"
output_file = "modified_podcast.xml"
modify_podcast_rss(input_url,cache_file , output_file)