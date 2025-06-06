#!/usr/bin/env python3
import argparse
import subprocess
import os
import sys

def main():
    parser = argparse.ArgumentParser(description='Deploy fair3r_custom_overlay using Ansible')
    parser.add_argument('--action', choices=['deploy', 'update'], required=True, help='Action to perform')
    parser.add_argument('--env', choices=['test', 'demo', 'prod'], required=True, help='Environment to deploy to')
    parser.add_argument('--docker', action='store_true', help='Use Docker for deployment')
    parser.add_argument('--docker-image', help='Docker image to deploy')
    parser.add_argument('--docker-registry', default='registry.gitlab.com', help='Docker registry')
    parser.add_argument('--registry-username', help='Docker registry username')
    parser.add_argument('--registry-password', help='Docker registry password')
    parser.add_argument('--db-host', default='localhost', help='Database host')
    args = parser.parse_args()

    # Set the current directory to the script's directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Determine the target host based on the environment
    target_host = args.env

    # Determine which playbook to use
    playbook = 'ansible/docker_deploy.yml' if args.docker else 'ansible/deploy.yml'

    # Build the Ansible command
    cmd = [
        'ansible-playbook',
        '-i', 'ansible/inventory.ini',
        playbook,
        '-e', f'action={args.action}',
        '-e', f'context={args.env}',
        '-e', f'target_host={target_host}'
    ]

    # Add Docker-specific parameters if using Docker
    if args.docker:
        if not args.docker_image:
            print("Error: --docker-image is required when using --docker", file=sys.stderr)
            sys.exit(1)

        cmd.extend([
            '-e', f'docker_image={args.docker_image}',
            '-e', f'docker_registry={args.docker_registry}',
            '-e', f'db_host={args.db_host}'
        ])

        if args.registry_username:
            cmd.extend(['-e', f'registry_username={args.registry_username}'])

        if args.registry_password:
            cmd.extend(['-e', f'registry_password={args.registry_password}'])

    # Install Ansible collection
    try:
        subprocess.check_call(['ansible-galaxy', 'collection', 'install', '-r', 'deploy/ansible/requirements.yml'])
    except subprocess.CalledProcessError as e:
        print(f"Error installing Ansible collection: {e}", file=sys.stderr)
        sys.exit(1)
    # Run the Ansible command
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print(f"Error running Ansible: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
