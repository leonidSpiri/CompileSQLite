#!/usr/bin/env python3
import os
import subprocess
import argparse
import requests
import zipfile
import io


def check_dependency(command):
    try:
        subprocess.run(command, check=True, shell=True)
        print(f"Dependency '{command}' is installed.")
        return True
    except subprocess.CalledProcessError:
        print(f"Dependency '{command}' is not installed.")
        return False


def download_sql():
    zip_file_url = "https://www.sqlite.org/2018/sqlite-amalgamation-3260000.zip"
    print("Downloading sqlite archive...")
    r = requests.get(zip_file_url)
    print("Extracting sqlite archive")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall()
    os.rename("sqlite-amalgamation-3260000", "sqlite_build")
    try:
        os.remove("sqlite-amalgamation-3260000.zip")
    except OSError:
        pass


def create_cmake_file():
    cmake_content = """cmake_minimum_required(VERSION 3.10)
project(SQLite)
set(SOURCE_FILES sqlite3.c)
add_library(sqlite3 SHARED ${SOURCE_FILES})
target_include_directories(sqlite3 PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
if(WIN32)
    set_target_properties(sqlite3 PROPERTIES OUTPUT_NAME sqlite3dll)
endif()"""
    with open("CMakeLists.txt", "w") as cmake_file:
        cmake_file.write(cmake_content)


def compile_to_win():
    os.makedirs("build_windows")
    os.chdir("build_windows")
    subprocess.run(["cmake", "-G", "Ninja", ".."])
    subprocess.run(["cmake", "--build", ".", "--config", "Release"])
    os.chdir("..")


def compile_to_linux():
    os.makedirs("build_linux")
    os.chdir("build_linux")
    subprocess.run(["cmake", ".."])
    subprocess.run(["make"])
    os.chdir("..")


def create_docker_file():
    dockerfile_content = """FROM gcc:latest
WORKDIR /app
COPY . .
RUN cd build_linux && cmake .. && make
CMD ["bash"]"""
    with open("Dockerfile", "w") as dockerfile:
        dockerfile.write(dockerfile_content)


def run_docker_container():
    subprocess.run("docker build -t sqlite_builder .", shell=True)
    subprocess.run("docker run -it --name sqlite_container sqlite_builder", shell=True)


def create_virtual_machine():
    iso_file_url = "https://mirror.yandex.ru/centos/7/isos/x86_64/CentOS-7-x86_64-Minimal-2009.iso"
    print("Downloading CentOS-7-x86_64-Minimal-2009.iso...")
    requests.get(iso_file_url)

    vboxmanage_commands = [
        "vboxmanage createvm --name CentOS-VM --ostype RedHat_64 --register",
        "vboxmanage modifyvm CentOS-VM --memory 1024 --vram 16",
        "vboxmanage createhd --filename CentOS-VM.vdi --size 20480",
        "vboxmanage storagectl CentOS-VM --name SATA --add sata --controller IntelAHCI",
        "vboxmanage storageattach CentOS-VM --storagectl SATA --port 0 --device 0 --type hdd --medium CentOS-VM.vdi",
        "vboxmanage storagectl CentOS-VM --name IDE --add ide --controller PIIX4",
        "vboxmanage storageattach CentOS-VM --storagectl IDE --port 1 --device 0 --type dvddrive --medium CentOS-7-x86_64-Minimal-2009.iso",
        "vboxmanage modifyvm CentOS-VM --boot1 dvd --boot2 disk --boot3 none --boot4 none",
        "vboxmanage modifyvm CentOS-VM --nic1 nat",
        "vboxmanage modifyvm CentOS-VM --audio none",
        "vboxmanage startvm CentOS-VM"
    ]

    for command in vboxmanage_commands:
        subprocess.run(command, shell=True)


def job(is_linux_build=True, run_docker=True):
    print("Starting the job")
    print("Downloading sqlite archive")
    download_sql()
    os.chdir("sqlite_build")

    print("Creating CMakeLists.txt")
    create_cmake_file()

    if is_linux_build:
        print("Compiling cmake file to Linux")
        compile_to_linux()
    else:
        print("Compiling cmake file to Windows")
        compile_to_win()

    print("Creating Dockerfile")
    create_docker_file()

    print("Creating virtual machine")
    create_virtual_machine()

    if run_docker:
        print("Running docker container")
        run_docker_container()


if __name__ == '__main__':
    if check_dependency("apt --version"):
        # Check for Python3-requests
        check_dependency("apt-get install python3-requests -y")

        # Check for CMake
        check_dependency("apt install cmake -y")

    parser = argparse.ArgumentParser(description='Echo your input')
    parser.add_argument('platform', help='What is your platform? win || linux')
    parser.add_argument('--run-docker', '-t', help='Run docker container with compiled SQLite', action='store_true')
    args = parser.parse_args()

    if args.platform == "win":
        job(is_linux_build=False, run_docker=args.run_docker)
    else:
        job(is_linux_build=True, run_docker=args.run_docker)
