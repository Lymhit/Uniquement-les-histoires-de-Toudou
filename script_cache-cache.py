import argparse
import podcastparser
import xml.etree.ElementTree as ET
import urllib.request
import pprint
import re
import time
import json
import requests
import os
import numpy as np
from xml.dom import minidom
from mutagen.id3 import ID3, APIC, TIT2, TALB, TPE1
from io import BytesIO
from PIL import Image
from datetime import datetime, timedelta

def change_blue_to_pink(image_path, output_path):
    # Ouvrir l'image
    image = Image.open(image_path)

    # Redimensionner l'image à 256x256 pixels
    resized_image = image.resize((256, 256))

    # Convertir l'image en tableau numpy pour le traitement
    img_array = np.array(resized_image)

    # Changer les nuances de bleu en nuances de rose
    # Définir les plages de couleur pour le bleu
    blue_mask = ((img_array[:, :, 0] < 100) &
                 (img_array[:, :, 1] < 100) &
                 (img_array[:, :, 2] > 100))

    # Appliquer le changement de couleur
    img_array[blue_mask] = [255, 204, 102]  # Jaune

    # Convertir le tableau numpy de nouveau en image
    result_image = Image.fromarray(img_array)

    # Sauvegarder l'image modifiée
    result_image.save(output_path)

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

def download_and_tag_mp3(url, title):
    # URL du fichier MP3 et de l'image de couverture
    mp3_url = url
    cover_url = 'https://www.radiofrance.fr/s3/cruiser-production-eu3/2022/11/0e9a29ba-7954-47ae-b0c6-b8cb16efdf3d/1400x1400_rf_omm_0000037236_ite.jpg'
    # Télécharger le fichier MP3
    mp3_response = requests.get(mp3_url)
    temp_mp3_path = 'temp_music.mp3'
    with open(temp_mp3_path, 'wb') as mp3_file:
        mp3_file.write(mp3_response.content)
    # Télécharger l'image de couverture
    cover_response = requests.get(cover_url)
    cover_image = Image.open(BytesIO(cover_response.content))
    # Sauvegarder l'image de couverture localement
    cover_path = 'cover_cache-cache.jpg'
    cover_image.save('tmp_cover.jpg')
    change_blue_to_pink('tmp_cover.jpg', cover_path)
    # Ajouter les métadonnées au fichier MP3
    audio = ID3(temp_mp3_path)
    # Ajouter le titre, l'artiste et l'album
    audio['TIT2'] = TIT2(encoding=3, text=title)
    audio['TPE1'] = TPE1(encoding=3, text='Radio France')
    audio['TALB'] = TALB(encoding=3, text='Cache-cache')
    # Ajouter la couverture de l'album
    with open(cover_path, 'rb') as albumart:
        audio['APIC'] = APIC(
            encoding=3,
            mime='image/jpeg',
            type=3, # 3 is for the cover (front)
            desc='Cover',
            data=albumart.read()
        )
    # Sauvegarder les modifications
    audio.save()
    # Renommer le fichier MP3 avec le titre de la chanson
    final_mp3_path = f'{title.replace('/5 : ',' - ')}.mp3'
    os.rename(temp_mp3_path, final_mp3_path)
    # Supprimer le fichier image temporaire
    os.remove('tmp_cover.jpg')
    print(f"Fichier MP3 téléchargé et renommé avec succès : {final_mp3_path}")

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
    with open("log.json", "w") as log_file:
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
    toptitle='Uniquement Cache-cache de Toudou'
    topcover='https://github.com/Lymhit/Uniquement-les-histoires-de-Toudou/blob/main/cover_cache-cache.jpg?raw=true'
    ET.SubElement(channel, "title").text = toptitle
    ET.SubElement(channel, "link").text = parsed.get('link', '')
    ET.SubElement(channel, "description").text = parsed.get('description', '')
    ET.SubElement(channel, "language").text = parsed.get('language', '')
    ET.SubElement(channel, "copyright").text = parsed.get('generator', '')
    ET.SubElement(channel, "generator").text = parsed.get('generator', '')
    img = ET.SubElement(channel, "image")
    ET.SubElement(img, "url").text = topcover
    ET.SubElement(img, "title").text = toptitle
    ET.SubElement(img, "link").text = "https://www.radiofrance.fr/franceinter/podcasts/toudou"
    ET.SubElement(channel, "itunes:author").text = 'France Inter'
    ET.SubElement(channel, "itunes:category", {
        "text": str(parsed.get('itunes_categories', '')[0][0]),
    })
    ET.SubElement(channel, "itunes:explicit").text = 'no'
    ET.SubElement(channel, "itunes:image", {
        "href": topcover,
    })
    owners = ET.SubElement(channel, "itunes:owner")
    ET.SubElement(owners, "itunes:email").text = parsed.get('itunes_owner', '').get('email')
    ET.SubElement(owners, "itunes:name").text = parsed.get('generator', '')
    ET.SubElement(channel, "itunes:subtitle").text = toptitle
    ET.SubElement(channel, "itunes:summary").text = ''
    ET.SubElement(channel, "itunes:new-feed-url").text = parsed.get('new_url', '')
    ET.SubElement(channel, "pa:new-feed-url").text = parsed.get('new_url', '')
    ET.SubElement(channel, "podcastRF:originStation").text = '1'
    ET.SubElement(channel, "googleplay:block").text = 'yes'
    # Trier les épisodes par titre
    sorted_episodes = sorted(parsed['episodes'], key=lambda x: extract_number(x.get('title', '')), reverse=True)
    # Ajouter les épisodes triés et modifiés avec un élément file_size conditionnel
    episodes_added_list=set([])
    for episode in sorted_episodes:
        episode_nomber=ajouter_zeros(extract_number(episode.get('title', '')))
        if (episode.get('title', '').startswith("Cache-cache")) and (episode_nomber not in episodes_added_list) :
            item = ET.SubElement(channel, "item")
            title=f"{episode_nomber}/{episode['title'].replace('Cache-cache ', '').split('/')[1]}"
            print(episode_nomber)
            title= title.replace('/'+episode['title'].replace('Cache-cache ', '').split('/')[1].split(' : ')[0]+' : ',' - ')
            episodes_added_list.add(episode_nomber)
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
            ET.SubElement(item, "podcastRF:businessReference").text = '49744'
            index = url.find('49744')
            # Extraire la sous-chaîne souhaitée
            if index != -1:
                result = url[index-5:index+10]
                ET.SubElement(item, "podcastRF:magnetothequeID").text = result
                year=str(url[index-5:index-1]+"0101")
                date_obj = datetime.strptime(year, "%Y%m%d")
                # Ajouter jours
                new_date_obj = date_obj + timedelta(days=int(episode_nomber))
                gmtime = new_date_obj.timetuple()
            ET.SubElement(item, "pubDate").text = time.strftime("%a, %d %b %Y %H:%M:%S +2000", gmtime)
            # ET.SubElement(item, "pubDate").text = time.strftime("%a, %d %b %Y %I:%M:%S +2000", time.gmtime(episode.get('published', '')))
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
            parser = argparse.ArgumentParser(description='Télécharger et tagger un fichier MP3.')
            parser.add_argument('--mp3', action='store_true', help='Activer le téléchargement et le taggage du MP3')
            args = parser.parse_args()
            if args.mp3:
                download_and_tag_mp3(url, title)
    # Créer un arbre XML et l'écrire dans un fichier
    tree = ET.ElementTree(rss)
    tree.write(output_file, encoding='utf-8', xml_declaration=True)
    # # Utiliser minidom pour formater le XML avec indentation
    # pretty_xml = prettify(rss)
    # # Écrire le XML formaté dans un fichier
    # with open(output_file, "w") as f:
    #     f.write(pretty_xml)

def main():
    input_url = "https://radiofrance-podcast.net/podcast09/rss_23713.xml"
    cache_file = "podcast_cache_cache-cache.xml"
    output_file = "modified_podcast_cache-cache.xml"
    modify_podcast_rss(input_url,cache_file , output_file)

if __name__ == "__main__":
    main()