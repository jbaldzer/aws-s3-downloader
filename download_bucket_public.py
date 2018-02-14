#!/usr/bin/env python
# -*- coding: utf-8 -*-
import random, requests, time, re
import urllib
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import os 


def download_bucket_public(bucket):
    """Scrape the given bucket, including all pages"""
    request = requests.get(bucket.url, verify=False)

    #Be sure you are at the correct url.  
    #Sometimes https://s3.amazonaws.com/foo redirects to https://foo.s3.amazonaws.com/
    if "<Endpoint>" in request.text:
        redirect_link = "https://{endpoint}".format(endpoint=re.search("<Endpoint>(.+?)</Endpoint>", request.text).group(1))
        # print "-->> {url} redirected to {redirect_link}".format(url=url, redirect_link=redirect_link)
        bucket.url = redirect_link
        download_bucket_public(bucket)

    else:
        print "Total: {num_keys} keys found".format(num_keys=len(re.findall("<Key>(.+?)</Key>", request.text)))
        add_page(bucket, request)

        #Paginate and save until there is nothing left
        while "<IsTruncated>true</IsTruncated>" in request.text:
            #Get next set of results
            last_key = re.findall("<Key>(.+?)</Key>", request.text)[-1].encode('utf-8')
            url = '''{bucket_url}?list-type=2&start-after={last_key}'''.format(bucket_url=bucket.url, last_key=last_key)
            request = requests.get(url, verify=False)
            #Add the next set of results
            add_page(bucket, request)
            print "Total: {num_keys} keys found".format(num_keys=bucket.num_keys)

        #Close the XML file, if it is being created
        close_xml_file(bucket)


def add_page(bucket, request):
    """For a given page of the bucket, add the XML and download the files, as requested"""
    keys = re.findall("<Key>(.+?)</Key>", request.text)
    bucket.num_keys += len(keys)

    if bucket.get_xml:
        save_xml(bucket=bucket, xml=request.text.replace('<?xml version="1.0" encoding="UTF-8"?>','').encode('utf-8'))
    if bucket.download:
        download_files(bucket=bucket, keys=keys)


def download_files(bucket, keys):
    """Download the subset of bucket keys.  This will download inaccessible files as XML output"""
    for key in keys:
        key = key.encode('utf-8')
        file_name = '{output_folder}/{key}'.format(output_folder=bucket.output_folder, key=key).strip()
        #Don't re-download any 
        if not os.path.exists(file_name):
            #Only download items that are on the include list and not in the exclude list
            if not bucket.download_include or any(include.lower() in key.lower() for include in bucket.download_include):
                if not bucket.download_exclude or not any(exclude.lower() in key.lower() for exclude in bucket.download_exclude):
                    #Create the directory if it doesn't exist (needed for sub-directories)
                    if not os.path.exists(file_name):
                        os.makedirs(file_name)
                        os.rmdir(file_name)


                    #Try to download the file.  Some will fail because they are directories
                    url = '{url}/{key}'.format(url=bucket.url, key=key)
                    print "  Downloading %s" % (url)
                    try:
                        urllib.urlretrieve(url, file_name)
                        print "    FINISHED"
                    except IOError:
                        print "    FAIL"
                        pass
        else:
            print "  already downloaded {file_name}".format(file_name=file_name)


def save_xml(bucket, xml):
    """Add the given bucket page's XML to the XML output file"""
    #Create the directory if it doesn't exist
    if not os.path.exists(bucket.output_folder):
        os.makedirs(bucket.output_folder)

    xml = re.sub(r'<ListBucketResult xmlns=.*">', '', xml).strip()
    xml = xml.replace("</ListBucketResult>","")

    """Save the XML (e.g. page source code) for the bucket"""
    f = open(bucket.xml_output_file, "a+")
    if not f.read(1):
        f.write('''<?xml version="1.0" encoding="UTF-8"?><ListBucketResult>''')
    f.write('''\n{xml}'''.format(xml=xml))
    f.close()


def close_xml_file(bucket):
    """Close the XML file, if it was created"""
    if bucket.get_xml:
        f = open(bucket.xml_output_file, "a")
        f.write('''</ListBucketResult>''')
        f.close()
