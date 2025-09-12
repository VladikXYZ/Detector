import tifffile
import xml.etree.ElementTree as XML_parser
NM_PXL = 64
OFFSET = 55

def parse_scale(path:str = 'data/6768/00.tif'):
    if path.endswith(".tif"):
        with tifffile.TiffFile(path) as tif:
            text = tif.pages.first.tags["ImageDescription"].value
            cut = XML_parser.fromstring(text).find('.//DrawObject')
            x = float(cut.find('.//Location//X').text)
            w = float(cut.find('.//ImageSize//Width').text)
            unit = cut.find('.//MicronbarMeasureUint').text
            nm = float(cut.find('.//MicronbarValue').text)
            if unit == 'Micrometer': nm*=1000
            nm_pxl = (w-x-OFFSET)/nm
            scale = NM_PXL/nm_pxl
            print(scale)
            return scale
    raise Exception(f"{path} is not a tif file")