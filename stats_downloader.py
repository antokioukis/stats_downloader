import re
from shutil import copyfileobj
from os import chdir, rename
from os.path import exists
from bs4 import BeautifulSoup
from tqdm import tqdm
import FreeSimpleGUI as sg
import requests


def remove_tags(html_name):
    soup = BeautifulSoup(html_name, "html.parser")
    for data in soup(['style', 'script']):
        data.decompose()
    return ' '.join(soup.stripped_strings)


def get_stats(curr_monster):
    if exists(curr_monster + '.txt'):
        return 0
    URL = "https://roll20.net/compendium/dnd5e/" + curr_monster
    r = requests.get(URL)
    text = remove_tags(r.text)
    try:
        text = text.split('to fight! ')[1].split('View All Monsters')[0]
    except IndexError:
        return 1
    outfile_name = curr_monster + '.txt'
    outfile = open(outfile_name, 'w+')
    outfile.write(text)
    outfile.close()
    return 0


def read_file(filename):
    with open(filename) as f:
        content = f.readlines()
    content = [x.strip() for x in content]
    return content


def write_monster_spellbook(active_monster, curr_spell):
    outfile_spellsbook_name = active_monster + '_spells.txt'
    spellbook = open(outfile_spellsbook_name, 'a+')
    URL = "http://dnd5e.wikidot.com/spell:" + curr_spell.replace(' ', '-')
    r = requests.get(URL)
    spell_text = remove_tags(r.text)
    spell_index_1 = spell_text.find('Create a Page')
    spell_index_2 = spell_text.find('Spell Lists.')
    spell_res = spell_text[spell_index_1 + len('Create a Page') + 1: spell_index_2]
    spellbook.write(spell_res + '\n\n')
    spellbook.close()


def get_monster_spells(active_monster, input_line, clean_outfile):
    line_tokens = input_line.split('•')[1:]
    for active_token in line_tokens:
        clean_outfile.write('\t\t' + active_token.strip() + '\n')
        curr_spells = active_token.split(':')[1].split(',')
        for active_spell in curr_spells:
            write_monster_spellbook(active_monster, active_spell.strip())


def prettify_stats(active_monster, outfile_name, outfile_clean_name):
    stats_list = ['HP', 'AC', 'Size', 'STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
    content = ''.join(read_file(outfile_name))
    if content[:3] == 'HP:':
        return
    clean_outfile = open(outfile_clean_name, 'w+')
    for active_stat in stats_list:
        regular_expression_pattern = rf'{active_stat}\s(\S+)'
        #
        match = re.search(regular_expression_pattern, content)
        clean_outfile.write(active_stat + ':' + match.group(1) + '\n')
        content = re.sub(regular_expression_pattern, '', content)
    #
    idx1 = content.find('Traits')
    idx2 = content.find('Actions')
    idx3 = content.find('Show Attribute List')
    #
    if not idx1 == -1:
        clean_outfile.write('Traits:\n')
        res = content[idx1 + len('Traits') + 1: idx2]
        traits_list = res.split('.')[:-1]
        for line in traits_list:
            if '•' in line:
                clean_outfile.write('\tPrepared Spells.\n')
                get_monster_spells(active_monster, line, clean_outfile)
            else:
                clean_outfile.write(line + '\n')
    if not idx2 == -1:
        clean_outfile.write('Actions:\n')
        res = content[idx2 + len('Actions') + 1: idx3]
        traits_list = res.split('. ')[:-1]
        for line in traits_list:
            clean_outfile.write('\t' + line + '.\n')
    rename(outfile_clean_name, outfile_name)


def get_image(curr_monster):
    curr_monster = curr_monster.replace(' ', '-').lower() + ".jpg"
    if not exists(curr_monster):
        URL = "https://www.aidedd.org/dnd/images/" + curr_monster
        try:
            r = requests.get(URL, stream=True)
        except requests.exceptions.RequestException:
            return 1
        with open(curr_monster, 'wb') as f:
            r.raw.decode_content = True
            copyfileobj(r.raw, f)
    return 0


def print_failures(failure_list, tipos):
    if failure_list:
        print('Not Found ' + tipos + ' for:')
        for item in failure_list:
            print(item)


def process_entries(monster_list, output_folder):
    chdir(output_folder)
    not_found_stats_list = []
    not_found_images_list = []
    for active_monster in tqdm(monster_list):
        clean_monster_name = active_monster.strip()
        images_status = get_image(clean_monster_name)
        stats_status = get_stats(clean_monster_name)
        if images_status:
            not_found_images_list.append(clean_monster_name)
        if stats_status:
            not_found_stats_list.append(clean_monster_name)
        else:
            prettify_stats(clean_monster_name, clean_monster_name + '.txt', clean_monster_name + '_clean.txt')
    print_failures(not_found_images_list, 'Images')
    print_failures(not_found_stats_list, 'Stats')


layout = [  [sg.Text("Please input the monsters' names?"), sg.Input(size=30)],
            [sg.Text("Choose a folder: "), sg.FolderBrowse()],
            [sg.Button("Go"), sg.Button("Quit")]
        ]

window = sg.Window('DnD Downloader', layout)

while True:
    event, values = window.read()
    if event in [sg.WIN_CLOSED, "Quit"]:
        break
    if event == "Go":
        monsters = values[0].split(',')
        folder_selected = values['Browse']
        process_entries(monsters, folder_selected)
        break
window.close()
