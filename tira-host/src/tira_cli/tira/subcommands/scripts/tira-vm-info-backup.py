#!/usr/bin/env python3
import os
import sys
from itertools import groupby
import click
import glob
from rich.console import Console
from rich.pretty import Pretty
import json
import shutil
from filecmp import cmp, dircmp

########################################
TIRA_PATH = '/mnt/ceph/tira'
########################################
DATA_PATH = TIRA_PATH + '/data'
MODEL_PATH = TIRA_PATH + '/model'
STATE_PATH = TIRA_PATH + '/state'
BACKUP_PATH = TIRA_PATH + '/backup'
########################################
RUNS_PATH = DATA_PATH + '/runs'
########################################
USERS_PATH = MODEL_PATH + '/users'
SOFTWARES_PATH = MODEL_PATH + '/softwares'
VMS_PATH = MODEL_PATH + '/virtual-machines'
########################################
SUBMISSIONS_PATH = STATE_PATH + '/softwares'


########################################
def is_mounted_ceph():
    return os.path.ismount(TIRA_PATH)

def save_user_credentials(username, backup_folder, console):
    console.log('[bold black on white]Looking for user credentials from users.prototext')
    l = []
    list_of_users = []
    with open(f'{USERS_PATH}/users.prototext') as f:
        for key, group in groupby(f, lambda line: line.startswith('users')):
            if not key:
                group = list(group)
                l.append(group)
    for user in l:
        a = user[:-1]
        a = [field.strip() for field in a]
        a = [thing.split(':') for thing in a]
        a = {thing[0]: thing[1].strip() for thing in a if len(thing) == 2}
        a = {k: v.replace('"', "") for k, v in a.items()}
        list_of_users.append(a)
    try:
        credentials = [user for user in list_of_users if user['userName'] == f'{username}'][0]
        console.log(f"[bold green]Found user credentials")
        return {f"{backup_folder}/{username}/model": credentials}
    except:
        console.log(f"[bold red]No credentials for user {username}")


def save_virtual_machine_prototext(username, backup_folder, console):
    console.log(f'[bold black on white]Looking for VM prototext for user {username}')
    vm_prototext = f'{VMS_PATH}/{username}.prototext'
    if os.path.exists(vm_prototext):
        console.log(f"[bold green]Found user prototext file")
        return {f'{backup_folder}/{username}/model': vm_prototext}
    else:
        console.log(f"[bold red]No VM prototext for user {username}")


def save_user_runs(username, backup_folder, console):
    console.log(f'[bold black on white]Looking for run directories of user {username}')
    try:
        run_directories = glob.glob(f'{RUNS_PATH}/*/{username}')
        tasks = [d[-2] for d in [d.split('/') for d in run_directories]]
        if len(run_directories) > 0:
            data = {f'{backup_folder}/{username}/data/runs/{t}':d for d,t in zip(run_directories, tasks)}
            console.log(f"[bold green]Found a total of {sum([len(os.listdir(v)) for _,v in data.items()])} run directories for the following datasets: {tasks}")
            return data
        else:
            console.log("[bold red]No runs to save")
    except:
        console.log("[bold red]No runs to save")


def save_user_softwares_prototext(username, backup_folder, console):
    console.log(f'[bold black on white]Looking for software/prototext.files for user {username}')
    try:
        software_directories = glob.glob(f'{SOFTWARES_PATH}/*/{username}')
        tasks = [d[-2] for d in [d.split('/') for d in software_directories]]
        if len(tasks) > 0:
            console.log(f'[bold green]Found a softwares.prototext file for the following tasks: {tasks}')
            return {f'{backup_folder}/{username}/model/softwares/{t}': os.path.join(d, os.listdir(d)[0]) for d, t in
                    zip(software_directories, tasks)}
        else:
            console.log("[bold red]No softwares to save")
    except:
        console.log("[bold red]No softwares to save")


def save_user_softwares_submissions(username, backup_folder, console):
    console.log(f'[bold black on white]Looking for software submissions for user {username}')
    try:
        software_directory = f'{SUBMISSIONS_PATH}/{username}'
        num_softwares = len(os.listdir(software_directory))
        console.log(f"[bold green] Found a total of {num_softwares} software submissions.")
        return {f'{backup_folder}/{username}/state/softwares': software_directory}
    except:
        console.log(f"[bold red]No software submissions for user {username}")

@click.command()
@click.option('--username', '-u', help='Username whose data you want to backup', required=True)
@click.option('--backup-folder', '-f', help='Absolute path of the backup destination', default=BACKUP_PATH,
              required=True, show_default=True)
@click.option('--backup', '-b', default=False, is_flag=True, help="Use this flag when you're ready to backup the data",
              show_default=True)
@click.option('--verbose', '-v', default=False, is_flag=True, show_default=True)
def main(username, backup_folder, backup, verbose):
    destination_folder = f'{backup_folder}/{username}'
    console = Console(log_path=False, record=backup)
    if not is_mounted_ceph():
        console.log(f'[bold red]Please make sure {TIRA_PATH} is mounted and accessible.')
        sys.exit(0)
    user_credentials = save_user_credentials(username, backup_folder, console)
    if verbose:
        console.log(user_credentials)

    user_vm_prototext = save_virtual_machine_prototext(username, backup_folder, console)
    if verbose:
        console.log(user_vm_prototext)

    user_runs = save_user_runs(username, backup_folder, console)
    if verbose:
        console.log(user_runs)

    softwares_prototext = save_user_softwares_prototext(username, backup_folder, console)
    if verbose:
        console.log(softwares_prototext)

    softwares_submissions = save_user_softwares_submissions(username, backup_folder, console)
    if verbose:
        console.log(softwares_submissions)

    if backup:
        to_delete = []
        os.makedirs(f'{destination_folder}/logs', exist_ok=True)
        if click.confirm(f'Are you sure you want to backup the files to {destination_folder}?', abort=True, default=True):
            pass

        if os.path.exists(destination_folder):
            console.print(f"[red bold]{destination_folder} already exists!")
            if click.confirm('Do you want to re-run the backup?', abort=True, default=True):
                pass
        else:
            console.log(f'Now creating {destination_folder}')
        os.makedirs(destination_folder, exist_ok=True)
        console.log(f'Backing up to folder {destination_folder}')

        if user_credentials:
            console.log(f'[bold black on white]Now copying entry from users.prototext file')
            for folder, dictionary in user_credentials.items():
                os.makedirs(folder, exist_ok=True)
                with open(f'{folder}/{username}.json', 'w') as f:
                    json.dump(dictionary, f)

        if user_vm_prototext:
            console.log(f"[bold black on white]Now copying the virtual machine's .prototext file")
            for dst_d, src_f in user_vm_prototext.items():
                os.makedirs(dst_d, exist_ok=True)
                shutil.copy(src_f, dst_d)
                src_d = os.path.dirname(src_f)
                to_delete.append({'source_directory': src_d, 'destination_directory': dst_d, 'deleted':True})

        if user_runs:
            console.log(f"[bold black on white]Now copying all user runs")
            for dst_d, src_d in user_runs.items():
                os.makedirs(dst_d, exist_ok=True)
                shutil.rmtree(dst_d)
                shutil.copytree(src_d, dst_d)
                to_delete.append({'source_directory': src_d, 'destination_directory': dst_d, 'deleted':True})

        if softwares_prototext:
            console.log(f"[bold black on white]Now copying all software prototext files")
            for dst_d, src_d in softwares_prototext.items():
                os.makedirs(dst_d, exist_ok=True)
                shutil.copy(src_d, dst_d)
                to_delete.append({'source_directory': src_d, 'destination_directory': dst_d, 'deleted':True})

        if softwares_submissions:
            console.log(f"[bold black on white]Now copying all user submissions")
            for dst_d, src_d in softwares_submissions.items():
                os.makedirs(dst_d, exist_ok=True)
                shutil.rmtree(dst_d)
                shutil.copytree(src_d, dst_d)
                to_delete.append({'source_directory': src_d, 'destination_directory': dst_d, 'deleted':True})

        console.print(to_delete)
        with open(f'{destination_folder}/logs/delete.jsonl', 'w') as f:
            for entry in to_delete:
                f.write(json.dumps(entry) + "\n")
        console.save_html(f'{destination_folder}/logs/log.html', clear=False)
        console.save_text(f'{destination_folder}/logs/log.txt')


if __name__ == "__main__":
    main()
