
import argparse
import configparser
import sys
import os
import subprocess
import shutil
import collections
import json
import requests


# Main keys used in the ini file
URL = 'repository_url'
FOLDER = 'local_folder'
BASE_SHA = 'base_sha'
ZENODO_ID = 'zenodo'
DOI = 'doi'
# user override keys in the ini file
FORCE_RECLONE = 'force_clone'
FORCE_RESHA = 'force_sha'
FORCE_REZENODO = 'force_zenodo'

# Private keys (tokens etc)
ZENODO_SECTION = 'zenodo'
PRIVATE_SITE = 'site'
PRIVATE_TOKEN = 'token'
PRIVATE_INI = 'private.ini' # the file itself

#
HEADERS_JSON = {"Content-Type": "application/json"}

def create_ini_file():
    preferred_repos = ['hg-novice', 'git-novice', 'make-novice', 'matlab-novice-inflammation', 'python-novice-inflammation', 'r-novice-gapminder', 'r-novice-inflammation', 'shell-novice', 'sql-novice-survey', 'lesson-example', 'instructor-training', 'workshop-template']
    preferred_ini = 'auto.ini'

    config = configparser.ConfigParser()
    for r in preferred_repos:
        if r.startswith('dc:'):
            url = "git@github.com:datacarpentry/" + r[3:] + ".git"
        else:
            url = "git@github.com:swcarpentry/" + r + ".git"
        config[r] = {
        URL: url,
        FOLDER: ',,'+r,
        }

    save_ini_file(config, preferred_ini)

    print("Default ini file has been generated in <<", preferred_ini, ">>.")
    print("Copy and possibly modify this file.")
    print("You'll need to pass it's name to most other commands.")

def save_ini_file(cfg, ini_file):
    with open(ini_file, 'w') as configfile:
        cfg.write(configfile)

def read_ini_file(ini_file):
    cfg = configparser.ConfigParser()
    cfg.read(ini_file)
    return cfg

def git(*args, **kwargs):
    cmd = ["git"] + list(args)
    if 'getoutput' in kwargs:
        res = subprocess.check_output(cmd)
    else:
        res = subprocess.call()
        if res != 0:
            out("!!! git", *args, "RETURNED", res)
    return res

def gitfor(c, *args, **kwargs):
    cmd = ["git", "-C", c[FOLDER]] + list(args)
    if 'getoutput' in kwargs:
        res = subprocess.check_output(cmd)
    else:
        res = subprocess.call(cmd)
        if res != 0:
            out("!!! git -C", c[FOLDER], *args, "RETURNED", res)
    return res

def new_parser_with_ini_file(*args, **kwargs):
    parser = argparse.ArgumentParser(*args, **kwargs)
    parser.add_argument('ini_file')
    return parser

def out(*args):
    print(*(["#### "] + list(args) + [" ####"]))

def clone_missing_repositories():
    parser = new_parser_with_ini_file('Clone the repositories that are not already present.')
    args = parser.parse_args(sys.argv[1:])
    cfg = read_ini_file(args.ini_file)
    out("CLONING")
    for r in cfg.sections():
        out("***", r)
        c = cfg[r]
        if os.path.isdir(c[FOLDER]):
            if FORCE_RECLONE in c:
                out("removing (forced)", c[FOLDER])
                shutil.rmtree(c[FOLDER])
        if os.path.isdir(c[FOLDER]):
            out("skipped...")
        else:
            git("clone", c[URL], c[FOLDER])

def fill_missing_basesha_with_latest():
    parser = new_parser_with_ini_file('Adds the base sha in the ini file, for those who are not present.')
    args = parser.parse_args(sys.argv[1:])
    cfg = read_ini_file(args.ini_file)
    out("SETTING BASE SHA")
    for r in cfg.sections():
        out("***", r)
        c = cfg[r]
        if BASE_SHA not in c or FORCE_RESHA in c:
            sha = gitfor(c, "rev-parse", "gh-pages", getoutput=True)
            c[BASE_SHA] = sha.decode('utf-8').replace('\n', '')
            out("set sha", c[BASE_SHA])
    save_ini_file(cfg, args.ini_file)

def create_missing_zenodo_submission():
    parser = new_parser_with_ini_file('Creating Zenodo submission for those who have none.')
    args = parser.parse_args(sys.argv[1:])
    cfg = read_ini_file(args.ini_file)
    out("CREATING ZENODO ENTRY")
    zc = read_ini_file(PRIVATE_INI)[ZENODO_SECTION]
    zenodo_site = zc.get(PRIVATE_SITE) or 'zenodo.org'
    create_url = 'https://{}/api/deposit/depositions/?access_token={}'.format(zenodo_site, zc[PRIVATE_TOKEN])
    for r in cfg.sections():
        out("***", r)
        c = cfg[r]
        if ZENODO_ID not in c or FORCE_REZENODO in c:
            req = requests.post(create_url, data="{}", headers=HEADERS_JSON)
            json = req.json()
            c[ZENODO_ID] = str(json['id'])
            c[DOI] = json['metadata']['prereserve_doi']['doi']
            out("got new zenodo id", c[ZENODO_ID])
    save_ini_file(cfg, args.ini_file)

#curl -i -H "Content-Type: application/json" -X POST --data '{"metadata": {"title": "My first upload", "upload_type": "poster", "description": "This is my first upload", "creators": [{"name": "Doe, John", "affiliation": "Zenodo"}]}}'


####################################################

commands_map = collections.OrderedDict()
commands_map['ini'] = create_ini_file
commands_map['clone-missing'] = clone_missing_repositories
commands_map['fill-missing-sha'] = fill_missing_basesha_with_latest
commands_map['create-missing-zenodo'] = create_missing_zenodo_submission

def usage(info):
    print("USAGE",'('+str(info)+')')
    print("Available commands:")
    for c in commands_map.keys():
        print(" -", c)

def main():
    if len(sys.argv) <= 1:
        usage(1)
    else:
        command = sys.argv[1]
        sys.argv = [' '.join(sys.argv[:2])] + sys.argv[2:]
        if command in commands_map.keys():
            commands_map[command]()
        else:
            usage(2)

if __name__ == '__main__':
    main()