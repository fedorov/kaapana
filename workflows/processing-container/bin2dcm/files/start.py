import sys
import os
import glob
import pydicom
import binascii
import pathlib
from datetime import datetime
from xml.dom import minidom
import xml.etree.ElementTree as et
from subprocess import PIPE, run

converter_count = 0


def combine_split_files(split_files_dir,delete_parts=True):
    input_files = sorted(glob.glob(os.path.join(split_files_dir, "*.part*")))
    input_files = [i for i in input_files if "part" in i.split(".")[-1]]
    suffixes = ''.join(pathlib.Path(input_files[0].split(".part")[0]).suffixes)
    final_filename = f"{input_files[0].split('---')[0]}{suffixes}"

    my_cmd = ['cat'] + input_files
    with open(final_filename, "w") as outfile:
        output = run(my_cmd, stdout=outfile)

    if output.returncode != 0:
        print(f"# Could not combine split files for {final_filename}!")
        print(output)
        exit(1)
    else:
        print(f"# Successfully created {final_filename}!")
        
        if delete_parts:
            for part_file in input_files:
                os.remove(part_file)

    return final_filename


def split_file(file_path, size_limit):
    command = ["split", "-b", f"{size_limit}M", file_path, f"{file_path}.part"]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)

    if output.returncode != 0:
        print("# Could not convert dicom to xml!")
        print(output)
        exit(1)

    part_files = sorted(glob.glob(f"{file_path}.part*"))
    return part_files


def xml_to_dicom(target_dir, delete_xml=True):
    global converter_count

    xml_files = sorted(glob.glob(os.path.join(target_dir, "*.xml")))

    dicom_list = []

    for xml_path in xml_files:
        dcm_path = xml_path.replace("xml", "dcm")
        print("#")
        print(f"# convert XML to DICOM: {xml_path} -> {dcm_path}")
        command = ["xml2dcm", xml_path, dcm_path]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=320)

        if output.returncode != 0:
            print("# Could not convert XML to DICOM!")
            print(output)
            exit(1)
        else:
            print("# DICOM created!")
            dicom_list.append(dcm_path)
            if delete_xml:
                os.remove(xml_path)

    converter_count += 1
    return dicom_list


def dicom_to_xml(dicom_dir, target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    dcm_files = sorted(glob.glob(os.path.join(dicom_dir, "*.dcm")))
    if len(dcm_files) == 0:
        print("#")
        print(f"# No DICOM file found at {dicom_dir} !")
        print("# ABORT")
        print("#")
        exit(1)
    
    generated_xml_list = []
    for dcm_file in dcm_files:
        xml_path = dcm_file.replace("dcm","xml")
        
        print("#")
        print(f"# convert DICOM to XML: {dcm_file} -> {xml_path}")

        command = ["dcm2xml", "+Eh", "+Wb", "--load-all", dcm_file, xml_path]
        print("#")
        print(f"# command: {command}")
        print("#")
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=320)

        if output.returncode != 0:
            print("# Could not convert dicom to xml!")
            print(output)
            exit(1)
        else:
            print("# XML created!")
            generated_xml_list.append(xml_path)

    return generated_xml_list


def xml_to_binary(target_dir,delete_xml=True):
    global converter_count
    xml_files = sorted(glob.glob(os.path.join(target_dir, "*.xml")))

    print("#")
    print("# starting xml_to_binary")
    print(f"# xml-dir:      {target_dir}")
    print("#")

    for xml_file in xml_files:
        context = et.iterparse(xml_file, events=("start", "end"))
        context = iter(context)
        ev, root = next(context)

        filename = None
        hex_data = None
        for ev, el in context:
            if ev == 'start' and el.tag == 'element' and el.attrib['name'] == "ImageComments":
                filename = el.text
                print(f"# Found filename: {filename}")
                expected_file_count = int(filename.split(".")[0].split("---")[1])
                if len(xml_files) != expected_file_count:
                    print("# ERROR!!")
                    print("#")
                    print(f"# Expected {expected_file_count} files -> found {len(xml_files)}")
                    print("# Abort")
                    print("#")
                    exit(1)

                filename = filename.replace("---1","")
                root.clear()
            elif ev == 'end' and el.tag == 'element' and el.attrib['tag'] == "7fe0,0010" and el.attrib['name'] == "PixelData":
                hex_data = el.text.strip().replace("\\", "")
                print("# Found Hex-Data!")
                root.clear()
            elif ev == 'end' and el.tag == 'pixel-item' and el.attrib['binary'] == "yes":
                hex_data = el.text.strip().replace("\\", "")
                print("# Found Hex-Data!")
                root.clear()

        if filename is None or hex_data is None:
            print("# Could not extract needed data!")
            print("#")
            print(f"# filename: {filename}")
            print(f"# hex_data: {hex_data}")
            print("#")
            exit(1)
        
        switched_hex = ""
        for x in range(0,len(hex_data),4):
            switched_hex+=hex_data[x+2:x+4]+hex_data[x:x+2]

        binary_path = os.path.join(os.path.dirname(xml_file), filename)
        binstr = binascii.unhexlify(switched_hex)
        with open(binary_path, "wb") as f:
            f.write(binstr)

        print(f"# Successfully extracted file: {filename} !")
        if delete_xml:
            os.remove(xml_file)

    if expected_file_count > 1:
        combine_split_files(split_files_dir=target_dir)

    converter_count += 1


def generate_xml(binary_path, target_dir, template_path="/template.xml"):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    size_limit = int(os.getenv("SIZE_LIMIT_MB", "100"))
    study_description = os.getenv("STUDY_DESCRIPTION", "Binary file")
    study_uid = os.getenv("STUDY_UID", pydicom.uid.generate_uid())
    series_uid = pydicom.uid.generate_uid()

    patient_id = os.getenv("PATIENT_ID", "Kaapana bin2dcm")
    study_id = os.getenv("STUDY_ID", "Kaapana bin2dcm")

    study_date = datetime.now().strftime("%Y%m%d")
    study_time = datetime.now().strftime("%H%M%S")
    study_datetime = datetime.now().strftime("%Y%m%d%H%M%S")  # YYYYMMDDHHMMSS
    print(f"# study_date: {study_date}")
    print(f"# study_time: {study_time}")

    xml_output_list = []

    binary_file_size = os.path.getsize(binary_path) >> 20

    binary_path_list = [binary_path]
    if size_limit != 0 and binary_file_size > size_limit:
        binary_path_list = split_file(file_path=binary_path, size_limit=size_limit)

    split_part_count = len(binary_path_list)
    full_filename = os.path.basename(binary_path)
    for i in range(0,len(binary_path_list)):
        binary_path = binary_path_list[i]
        series_uid = pydicom.uid.generate_uid()
        sopInstanceUID = pydicom.uid.generate_uid()
        version_uid = pydicom.uid.generate_uid()

        filename = os.path.basename(binary_path)
        new_filename = filename.split('.')[0]+f"---{split_part_count}{''.join(pathlib.Path(filename).suffixes)}"
        xml_output_path = os.path.join(target_dir, f"{new_filename}.xml")

        xml_template = minidom.parse(template_path)

        # with open(binary_path, 'rb') as f:
        #     hex_data = f.read().hex("\\")
        # xml_template.getElementsByTagName('pixel-item')[0].firstChild.data = hex_data

        elements = xml_template.getElementsByTagName('element')
        for element in elements:
            el_name = element.attributes['name'].value

            if el_name == "PatientName":
                pass
                # element.firstChild.data = patient_id

            elif el_name == "InstanceCreationDate" or el_name == "StudyDate" or el_name == "ContentDate":
                element.firstChild.data = study_date

            elif el_name == "InstanceCreationTime" or el_name == "StudyTime" or el_name == "ContentTime":
                element.firstChild.data = study_time

            elif el_name == "AcquisitionDateTime":
                element.firstChild.data = study_datetime

            elif el_name == "StudyInstanceUID":
                element.firstChild.data = study_uid

            elif el_name == "StudyID":
                element.firstChild.data = study_id

            elif el_name == "PatientID":
                element.firstChild.data = patient_id

            elif el_name == "SeriesNumber":
                element.firstChild.data = "1"

            elif el_name == "ImageComments":
                element.firstChild.data = new_filename

            elif el_name == "SeriesDescription":
                element.firstChild.data = ""

            elif el_name == "InstanceNumber" or el_name == "ReferencedFrameNumber":
                element.firstChild.data = str(i)

            elif el_name == "CreatorVersionUID":
                element.firstChild.data = version_uid

            elif el_name == "StudyDescription":
                element.firstChild.data = study_description

            elif el_name == "SeriesInstanceUID":
                element.firstChild.data = series_uid

            elif el_name == "MediaStorageSOPInstanceUID" or el_name == "SOPInstanceUID":
                element.firstChild.data = sopInstanceUID

            elif el_name == "file":
                element.firstChild.data = binary_path

            if el_name != "file" and 'len' in element.attributes and len(element.childNodes) > 0:
                element.attributes['len'].value = str(len(element.firstChild.data))
                element.attributes['vm'].value = "1"
                print(f"# {el_name}: {element.firstChild.data} : {element.attributes['len'].value}")

        print("# Generated XML from template -> export file...")
        with open(xml_output_path, "w") as xml_file:
            xml_template.writexml(xml_file)

        xml_output_list.append(xml_output_path)

    return xml_output_list



# START
binary_file_extensions = os.getenv("EXTENSIONS", "*.zip").split(",")
batch_folders = [f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))]

for batch_element_dir in batch_folders:
    element_input_dir = os.path.join(batch_element_dir, os.getenv("OPERATOR_IN_DIR", ""))
    element_output_dir = os.path.join(batch_element_dir, os.getenv("OPERATOR_OUT_DIR", ""))

    binaries_found = []
    for extension in binary_file_extensions:
        binaries_found.extend(glob.glob(os.path.join(element_input_dir, extension)))

    if len(binaries_found) == 0:
        print("############### No binaries found at {} ".format(element_input_dir))
        print("############### Extensions: {} ".format(binary_file_extensions))
        continue

    convert_binary = False
    for binary in binaries_found:
        if not os.path.exists(element_output_dir):
            os.makedirs(element_output_dir)
        print("##################################################")
        print("#")
        print("# Found file: {}".format(binary))
        print("#")
        if ".dcm" in binary:
            print("# --> identified DICOM --> execute dcm2binary")
            print("#")
            print("# --> extract xml")
            extracted_xml = dicom_to_xml(dcm_path=binary, target_dir=element_output_dir)
            print("#")
            convert_binary = True

        else:
            print("# --> no DICOM --> execute bin2dcm")
            print(f"# --> generate_xml -> {element_output_dir}")
            generated_xml_list = generate_xml(binary_path=binary, target_dir=element_output_dir)
            print("#")
            print("# --> xml_to_dicom")
            dcm_path_list = xml_to_dicom(target_dir=element_output_dir)
            print("#")

    if convert_binary:
        print("# --> get_binary_from_xml")
        xml_to_binary(target_dir=element_output_dir)
        print("#")

print("##################################################")
print("#")
print("# Searching for files on batch-level....")
print("#")
print("##################################################")
print("#")

batch_input_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_IN_DIR'])
batch_output_dir = os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['OPERATOR_OUT_DIR'])

print(f"# batch_input_dir:  {batch_input_dir}")
print(f"# batch_output_dir: {batch_output_dir}")
# if "bcm2bin" in batch_output_dir:
#     batch_output_dir="/data/dcm2bin"
# print(f"# batch_output_dir: {batch_output_dir}")

binaries_found = []
for extension in binary_file_extensions:
    binaries_found.extend(glob.glob(os.path.join(batch_input_dir, extension)))

if len(binaries_found) == 0:
    print("############### No binaries found at {} ".format(batch_input_dir))
    print("############### Extensions: {} ".format(binary_file_extensions))

convert_binary = False
for binary in binaries_found:
    if not os.path.exists(batch_output_dir):
        os.makedirs(batch_output_dir)
    print("#")
    print("# Found file: {}".format(binary))
    print("#")
    if ".dcm" in binary:
        print("# --> identified DICOM --> execute dcm2binary")
        print("#")
        print(f"# --> extract xml: {binary} -> {batch_output_dir}")
        extracted_xml = dicom_to_xml(dcm_path=binary, target_dir=batch_output_dir)
        print("#")
        convert_binary = True

    else:
        print("# --> no DICOM --> execute bin2dcm")
        print("#")
        print(f"# --> generate_xml: {binary} -> {batch_output_dir}")
        print("#")
        generated_xml_list = generate_xml(binary_path=binary, target_dir=batch_output_dir)
        print(f"# --> xml_to_dicom: {generated_xml_list} -> {batch_output_dir}")
        print("#")
        dcm_path_list = xml_to_dicom(target_dir=batch_output_dir)

if convert_binary:
    print("# --> get_binary_from_xml")
    xml_to_binary(target_dir=batch_output_dir)
    print("#")


if converter_count == 0:
    print("#")
    print("##################################################")
    print("#")
    print("#################  ERROR  #######################")
    print("#")
    print("# ----> NO FILES HAVE BEEN CONVERTED!")
    print("#")
    print("##################################################")
    print("#")
    exit(1)

print("#")
print("#")
print("##################################################")
print("#")
print("##################  DONE  ########################")
print("#")
print("##################################################")
print("#")
print("#")
