#!/usr/bin/env python3
import os
import subprocess
import argparse
import requests
import zipfile
import io


def download_sql():
    zip_file_url = "https://www.sqlite.org/2018/sqlite-amalgamation-3260000.zip"
    r = requests.get(zip_file_url)
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
RUN mkdir build_linux && cd build_linux && cmake .. && make
CMD ["bash"]"""
    with open("Dockerfile", "w") as dockerfile:
        dockerfile.write(dockerfile_content)


def job(is_linux_build=True):
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Echo your input')
    parser.add_argument('platform', help='What is your platform? win || linux')
    args = parser.parse_args()

    if args.platform == "win":
        job(is_linux_build=False)
    else:
        job(is_linux_build=True)
