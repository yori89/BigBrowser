#!/usr/bin/env python

import sys
import os
import threading
import argparse
import datetime

from selenium import webdriver
from bs4 import BeautifulSoup

PROGRESS = 0


def read_url_list(filename):
    url_file = open("urls.txt", "r")
    urls =  [ url.rstrip('\n') for url in url_file.readlines() ]
    url_file.close()
    return urls


def extract_nmap_xml(filename):
    xml_file = open(filename, 'r')
    soup = BeautifulSoup(xml_file, 'lxml')
    urls = []

    for host in soup.find_all('host'):
        ip_addr = host.address["addr"]
        for port in host.ports.find_all('port'):
            if port.state["state"] == "open":
                if port.service["name"] in ["http", "https"]:
                    if port.service.has_attr('tunnel') and port.service["tunnel"] == "ssl":
                        url = "https://"
                    else:
                        url = "http://"
                    url += ip_addr + ":" + port["portid"]
                    urls.append(url)
    return urls


def take_screenshots(url_set, nb_threads):
    global PROGRESS
    driver = webdriver.PhantomJS(service_args=['--ignore-ssl-errors=true', '--ssl-protocol=any'])
    driver.set_window_size(800, 600)
    for url in url_set:
        try:
            driver.get(url)
            sc_file = 'pics/' + url.split('://')[1] + ".png"
            driver.save_screenshot(sc_file)
            PROGRESS +=  100.0 / len(url_set) / nb_threads
            print "[" + str(int(PROGRESS)) + "%] Downloading: " + url + " > " + sc_file
        except Exception as exc:
            print exc
    driver.quit()


def generate_report(urls, nb_threads=5, report_name="report.html"):
    os.makedirs("pics/")
    html_file = open(report_name, "w")
    html_file.write('''
    <html>
    <head>
    </head>
    <body style="background: black">
    <table>
    '''
    )
    col = 0
    for url in urls:
        sc_file = 'pics/' + url.split('://')[1] + ".png"
        if col == 0:
            html_file.write('<tr>')
        html_file.write('<td style="text-align:center"><div style="height:600px;overflow:hidden"><a href="' \
            + sc_file + '"><img style="height:60%;width:80%;background:white;" src="' + sc_file + \
            '"/></a><strong><a target="_blank" href="'+ url + '" style="color: white">' + url + '</a></strong></div></td>')
        if col == 3:
            html_file.write('</tr>')
        col = (col + 1) % 4
    html_file.write('''
    </table>
    </body>
    </html>
    '''
    )
    html_file.close()
    thread_load = len(urls) / nb_threads
    threads = []
    for i in range(nb_threads):
        if i == (nb_threads - 1):
            threads.append(threading.Thread(target=take_screenshots, args=(urls[i * thread_load:], nb_threads)))
        else:
            threads.append(threading.Thread(target=take_screenshots, args=(urls[i * thread_load:(i + 1) * thread_load ], nb_threads)))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    print "[*] Report generated: file://" + os.path.join(os.getcwd(), report_name)


def main():
    parser = argparse.ArgumentParser(description="Generates a HTML report with screenshots of all found web servers. Input can be either a text file with one URL per line, or nmap XML output")
    parser.add_argument("file", help="Nmap XML output or text file with one URL per line")
    parser.add_argument("-t", "--threads", help="Number of threads")
    parser.add_argument("-o", "--output", help="Name of the generated report")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print "File not found: " + args.file
        exit(0)

    filetype="txt"
    with open(args.file, "r") as f:
        for line in f:
            if "<!DOCTYPE nmaprun>" in line:
                filetype = "nmap"
    urls = None
    if filetype == "nmap":
        urls =extract_nmap_xml(args.file)
    else:
        urls = read_url_list(args.file)

    report_name = "bigbrowser_report"
    if args.output:
        report_name = args.output
    if os.path.exists(report_name):
        print "Folder exists: %s" % report_name
        exit(0)
    os.makedirs(report_name)
    os.chdir(report_name)
    
    if args.threads:
        nb_threads = int(args.threads)
    else:
        nb_threads = 5
    generate_report(urls, nb_threads, report_name=report_name + ".html")


if __name__ == "__main__":
    main()
