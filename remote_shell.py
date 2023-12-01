import paramiko
import pexpect
from paramiko import SSHClient
import os
import sys
import time
import subprocess
from scp import SCPClient
import zipfile
import datetime

def invoke_shell(cmd, host, username, password, timeout=120):
    # Simple utility method to ssh to remote machines
    try:
        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, port=22, username=username, password=password, timeout=timeout)
        _stdin, _stdout, _stderr = client.exec_command(cmd)
        output = _stdout.read().decode()
        error = _stderr.read().decode()
        exitcode = _stdout.channel.recv_exit_status()
        if exitcode==0:
            return output.strip(), exitcode
        else:
            return error.strip(), exitcode
    except Exception as e:
        logger().error("Couldn't execute command: %s" %str(e))
        raise e
    finally:
        client.close()


# Function to run a command in powershell in a remote windows machine as administrator
def run_remote_powershell_as_administrator(cmd, host, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the remote host
        client.connect(host, username=username, password=password)
        session_cmd = f'Start-Process -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "{cmd}" -Verb RunAs'
        stdin, stdout, stderr = client.exec_command(session_cmd)

        # Print the output
        output = stdout.read().decode()
        error = stderr.read().decode()
        exitcode = stdout.channel.recv_exit_status()
        if exitcode==0:
            return output.strip(), exitcode
        else:
            return error.strip(), exitcode
    finally:
        client.close()

# This method is to run a command in powershell in a remote windows machine
def run_in_powershell(cmd, host, username, password, timeout=600):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # command = f'cd wsautomation | powershell -Command \'{cmd}\' | Exit'
    #command = f'powershell -Command "cd wsautomation; \'{cmd}\'; Exit"'
    #print(command)
    try:
        ssh_client.connect(host, username=username, password=password)
        stdin, stdout, stderr = ssh_client.exec_command("powershell.exe -Command {}".format(cmd))
        # stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)
        output = stdout.read().decode()
        error = stderr.read().decode()
        exitcode = stdout.channel.recv_exit_status()

        while not stdout.channel.exit_status_ready():
            counter+=5
            if counter==timeout/5:
                break
            time.sleep(5)
        if exitcode==0:
            print(output.strip())
            return output.strip(), exitcode
        else:
            print(error.strip())
            return error.strip(), exitcode
    except Exception as e:
        logger().error("Couldn't download file in remote vm: %s" %str(e))
        raise e
    finally:
        ssh_client.close()


# This method helps to download a file in a remote windows machine via curl command 
def remote_download(url, save_to, host, username, password, timeout=600):
    # Simple utility method to download files directly in remote machines
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=username, password=password)
    try:
        start_time = datetime.datetime.now()
        command = 'curl -o %s %s' %(save_to, url)
        print(command)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        exitcode = stdout.channel.recv_exit_status()
        end_time = datetime.datetime.now()
        logger().info("Download completed in %s seconds" %str(end_time-start_time))
        if exitcode==0:
            print(output)
            return output.strip(), exitcode
        else:
            return error.strip(), exitcode
    except Exception as e:
        logger().error("Couldn't download file in remote vm: %s" %str(e))
        raise e
    finally:
        client.close()



''' 
The below two methods will help to zip and copy a large file to a remote machine and unzip there
If the remote machine is windows, it uses tar to unzip
'''
def zip_directory(source_dir, zip_file):
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname=arcname)

def copy_directory_to_remote(local_dir, remote_dir, hostname, username, password, zip=True, linux=False):
    try:
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, port=22, username=username, password=password, timeout=30)

        # SCPCLient takes a paramiko transport as an argument
        # scp = SCPClient(ssh.get_transport(), progress=progress)
        logger().info("Zip source directory")
        scp = SCPClient(ssh.get_transport())
        if zip:
            zip_dir = local_dir + '.zip'
            zip_directory(local_dir, zip_dir)
            remote_zip_dir = remote_dir + '.zip'
            scp.put(zip_dir, remote_zip_dir)
            logger().info("Copied zip directory to remote")

            # Unzip the copied directory
            create_remote_directory(hostname=hostname, username=username, password=password, remote_directory=remote_dir)
            if linux:
                remote_dir = remote_dir + '/'
                cmd = f'unzip -q "{remote_zip_dir}" -d "{remote_dir}"'
                print(cmd)
            else:
                cmd = f'tar.exe -xf "{remote_zip_dir}" -C "{remote_dir}"'
            logger().info("Unzip at remote location")
            ssh.exec_command(cmd)

        else:
            scp.put(local_dir, recursive=True, remote_path=remote_dir)  
    except Exception as e:
        logger().error("Copy files failed - %s" %str(e))
        raise e
    finally:
        scp.close()
        ssh.close()


#This method will create a directory in a remote machine
def create_remote_directory(hostname, username, password, remote_directory):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(hostname, username=username, password=password)
        stdin, stdout, stderr = ssh.exec_command(f'mkdir "{remote_directory}"')
        output = stdout.read().decode()
        error = stderr.read().decode()
        exitcode = stdout.channel.recv_exit_status()
        logger().info(f"Remote directory '{remote_directory}' created successfully.")
    except paramiko.AuthenticationException:
        logger().error("Authentication failed. Please check the credentials.")
    except paramiko.SSHException as ssh_exception:
        logger().error(f"SSH error occurred: {str(ssh_exception)}")
    except Exception as e:
        logger().error(f"An error occurred: {str(e)}")
    finally:
        ssh.close()

# Delete a directory from a remote machine
def delete_remote_directory(hostname, username, password, remote_directory, linux=False):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(hostname, username=username, password=password)
        if linux:
            cmd = f'rm -rf "{remote_directory}"'
        else:
            cmd = f'rmdir /s /q "{remote_directory}"'
        stdin, stdout, stderr = ssh.exec_command(f'rmdir /s /q "{remote_directory}"')
        output = stdout.read().decode()
        error = stderr.read().decode()
        exitcode = stdout.channel.recv_exit_status()
        logger().info(f"Remote directory '{remote_directory}' deleted successfully.")
    except paramiko.AuthenticationException:
        logger().error("Authentication failed. Please check the credentials.")
    except paramiko.SSHException as ssh_exception:
        logger().error(f"SSH error occurred: {str(ssh_exception)}")
    except Exception as e:
        logger().error(f"An error occurred: {str(e)}")
    finally:
        ssh.close()


# Read a remote log file
def get_remote_log_contents(hostname, username, password, remote_path):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(hostname, username=username, password=password)
        with ssh.open_sftp() as sftp:
            with sftp.file(remote_path, "r") as remote_file:
                return remote_file.read().decode("utf-8")
    except paramiko.AuthenticationException:
        print("Authentication failed.")
    except paramiko.SSHException as e:
        print(f"SSH connection error: {e}")
    finally:
        ssh.close()

'''
This method is an example to run a python command that requires UI interaction remotely
This method requires PsExec.exe to be available in the remote machine
'''
def execute_ui_commands(host, username, password, timeout=600):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh_client.connect(host, username=username, password=password)
        python_cmd = "C:\autofoler\location\ui_script.py"
        cmd = 'C:\\Users\\myhome\\automation\\PSTools\\PsExec.exe /ACCEPTEULA \\\\DESKTOP-LQHGR9M -s -i 1 -u %s -p \'%s\' powershell -ExecutionPolicy Bypass /c \"%s\"' %(host, username, password, python_cmd)
        stdin, stdout, stderr = ssh_client.exec_command("powershell.exe -Command {}".format(cmd))
        output = stdout.read().decode()
        error = stderr.read().decode()
        exitcode = stdout.channel.recv_exit_status()

        while not stdout.channel.exit_status_ready():
            counter+=5
            if counter==timeout/5:
                break
            time.sleep(5)
        if exitcode==0:
            print(output.strip())
            return output.strip(), exitcode
        else:
            print(error.strip())
            return error.strip(), exitcode
    except Exception as e:
        logger().error("Couldn't download file in remote vm: %s" %str(e))
        raise e
    finally:
        ssh_client.close()


