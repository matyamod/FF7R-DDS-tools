import os, argparse
from io_util import *
from texture_asset import BYTE_PER_PIXEL, is_power_of_2

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='dds')
    args = parser.parse_args()
    return args

DDS_FORMAT = {
    'DXT1': ['DXT1', 71, 72], #DXGI_FORMAT_BC1_TYPELESS
    'DXT5/BC3': ['DXT5', 77, 78], #DXGI_FORMAT_BC3_TYPELESS	
    'BC4/ATI1': [80, 'ATI1', 'BC4U'], #DXGI_FORMAT_BC4_UNORM
    'BC5/ATI2': [83, 'ATI2', 'BC5U'], #DXGI_FORMAT_BC5_UNORM
    'BC6H(unsigned)': [95], #DXGI_FORMAT_BC6H_UF16
    'BC6H(signed)': [96], #DXGI_FORMAT_BC6H_SF16
    'BC7': [98, 99], #	DXGI_FORMAT_BC7_TYPELESS
    'FloatRGBA': [], #DXGI_FORMAT_R16G16B16A16_FLOAT?
    'B8G8R8A8(sRGB)': [91] #DXGI_FORMAT_B8G8R8A8_UNORM_SRGB
}

def get_dds_format(form):
    for k in DDS_FORMAT:
        if form in DDS_FORMAT[k]:
            return k
    raise RuntimeError('Unsupported DDS format. ({})'.format(form))

class DDS:
    HEADER = b'\x44\x44\x53\x20'
    def __init__(self, file, verbose=False, only_header=False):
        if file[-3:]!='dds' and not only_header:
            raise RuntimeError('Not DDS.')
        print('load: ' + file)
        with open(file, 'rb') as f:
            head = f.read(4)
            check(head, DDS.HEADER)
            read_const_uint32(f, 124)
            f.seek(4,1)
            self.height = read_uint32(f)
            self.width = read_uint32(f)
            f.seek(4,1)
            self.bin1=f.read(4)
            self.mipmap_num = read_uint32(f)
            self.mipmap_num += self.mipmap_num==0
            self.bin2=f.read(44)
            read_const_uint32(f, 32)
            self.bin3=f.read(4)
            self.fourCC=f.read(4).decode()
            self.bin4=f.read(20)
            f.seek(4, 1)
            self.bin5=f.read(16)
            
            if self.fourCC=='DX10':
                self.format=read_uint32(f)
                self.bin6=f.read(16)
            else:
                self.format=self.fourCC
            self.format_name = get_dds_format(self.format)

            self.byte_per_pixel = BYTE_PER_PIXEL[self.format_name]

            if only_header:
                return

            height=self.height
            width=self.width
            self.mipmap_data = []
            self.mipmap_size = []
            for i in range(self.mipmap_num):
                if height%4!=0:
                    height+=4-height%4
                if width%4!=0:
                    width+=4-width%4

                size = height*width*self.byte_per_pixel
                if size!=int(size):
                    raise RuntimeError('The size of mipmap data is not int. This is unexpected.')

                data = f.read(int(size))
                if verbose:
                    print('  Mipmap {}'.format(i))
                    print('    size (w, h): ({}, {})'.format(width, height))
                self.mipmap_data.append(data)
                self.mipmap_size.append([int(width), int(height)])

                height = height//2
                width = width//2

            self.print()
            check(f.tell(), get_size(f), msg='Parse Failed. This is unexpected.')
            if self.mipmap_num>1 and (not is_power_of_2(self.width) or not is_power_of_2(self.height)):
                print('Warning: Mipmaps should have power of 2 as its width and height. ({}, {})'.format(self.width, self.height))
            
    def print(self):
        print('  height: {}'.format(self.height))
        print('  width: {}'.format(self.width))
        print('  mipmap num: {}'.format(self.mipmap_num))
        print('  format: {}'.format(self.format_name))
        print('  byte per pixel: {}'.format(self.byte_per_pixel))
        #print(': {}'.format(self.))

    def inject(self, uasset):
        self.mipmap_data=[]
        if uasset.has_ubulk:
            for d in uasset.ubulk_data:
                self.mipmap_data.append(d)
        for d in uasset.uexp_map_data_list:
            self.mipmap_data.append(d)
        self.mipmap_num=len(self.mipmap_data)
        self.width, self.height = uasset.get_max_size()

    def save(self, file, only_header=False):
        with open(file, 'wb') as f:
            f.write(DDS.HEADER)
            write_uint32(f, 124)
            write_uint8(f, 7)
            write_uint8(f, 16)
            write_uint8(f, 8+2*(self.mipmap_num>1))
            write_uint8(f, 0)
            write_uint32(f, self.height)
            write_uint32(f, self.width)
            write_uint32(f, int(self.width*self.height*self.byte_per_pixel))
            f.write(self.bin1)
            write_uint32(f, self.mipmap_num)
            f.write(self.bin2)
            write_uint32(f, 32)
            f.write(self.bin3)
            f.write(self.fourCC.encode())
            f.write(self.bin4)
            write_uint8(f, (self.mipmap_num>1)*8)
            write_uint8(f, 16)
            write_uint8(f, (self.mipmap_num>1)*64)
            write_uint8(f, 0)
            f.write(self.bin5)

            if self.fourCC=='DX10':
                write_uint32(f, self.format)
                f.write(self.bin6)

            if only_header:
                return

            for d in self.mipmap_data:
                f.write(d)
