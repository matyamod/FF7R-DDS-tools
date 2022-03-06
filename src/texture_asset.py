import os
from io_util import *
from uasset import Uasset

# UE4 format: [dds format, byte per pixel]
BYTE_PER_PIXEL = {
    'DXT1': 0.5,
    'BC4/ATI1': 0.5,
    'BC5/ATI2': 1,
    'BC6H(unsigned)': 1,
    'BC6H(signed)': 1,
    'FloatRGBA': 8,
    'B8G8R8A8(sRGB)': 4
}

PF_FORMAT = {
    'PF_DXT1': 'DXT1',
    'PF_BC4': 'BC4/ATI1',
    'PF_BC5': 'BC5/ATI2',
    'PF_BC6H': 'BC6H(unsigned)',
    'PF_FloatRGBA': 'FloatRGBA',
    'PF_B8G8R8A8': 'B8G8R8A8(sRGB)'
}   

def is_power_of_2(n):
    if n==1:
        return True
    if n%2!=0:
        return False
    return is_power_of_2(n//2)

class MipmapMetadata:
    def __init__(self, data_size, offset, size, uexp):
        self.uexp=uexp
        if uexp:
            self.flag=32
            self.data_size=0
        else:
            self.flag=66817
            self.data_size=data_size
        self.offset=offset
        self.width=size[0]
        self.height=size[1]
        self.pixel_num = self.width*self.height

    def read(f, uexp=True):
        read_const_uint32(f, 1) #Entry Indicator?
        flag = read_uint32(f)        
        data_size = read_uint32(f)
        if uexp:
            check(flag, 32)
            check(data_size, 0)
        else:
            check(flag, 66817)
        read_const_uint32(f, data_size)
        offset = read_uint32(f)
        read_null(f)
        width = read_uint32(f)
        height = read_uint32(f)
        return MipmapMetadata(data_size, offset, [width, height], uexp)

    def print(self, padding=2):
        pad = ' '*padding
        print(pad + 'file: ' + 'uexp'*self.uexp + 'ubluk'*(not self.uexp))
        if not self.uexp:
            print(pad + 'data size: {}'.format(self.data_size))
        print(pad + 'metadata'*self.uexp + 'texture data'*(not self.uexp) + ' offset: {}'.format(self.offset))
        print(pad + 'width: {}'.format(self.width))
        print(pad + 'height: {}'.format(self.height))

    def to_uexp(self):
        self.flag=32
        self.data_size=0
        self.uexp=True

    def write(self, f, uasset_size):
        new_offset = f.tell() + uasset_size+24
        write_uint32(f, 1)
        write_uint32(f, self.flag)
        write_uint32(f, self.data_size)
        write_uint32(f, self.data_size)
        if self.uexp:
            write_uint32(f, new_offset)
        else:
            write_uint32(f, self.offset)
        write_null(f)

        write_uint32(f, self.width)
        write_uint32(f, self.height)

EXT = ['.uasset', '.uexp', '.ubulk']
UNREAL_SIGNATURE = b'\xC1\x83\x2A\x9E'
UBULK_FLAG = [0, 16384]

def get_all_file_path(file, rebase=False, folder=''):
    if rebase:
        file=os.path.basename(file)
        file=os.path.join(folder, file)
    base_name, ext = os.path.splitext(file)

    if ext not in EXT:
        raise RuntimeError('Not Uasset. ({})'.format(file))

    return [base_name + ext for ext in EXT]

class TextureUasset:
    
    def __init__(self, file_path, verbose=False):

        if not os.path.isfile(file_path):
            raise RuntimeError('Not File. ({})'.format(file_path))

        uasset_name, uexp_name, ubulk_name = get_all_file_path(file_path)

        self.has_ubulk = os.path.exists(ubulk_name)

        #print(uasset_name)
        #print(uexp_name)
        #if self.has_ubulk:
        #    print(ubulk_name)

        self.uasset = Uasset(uasset_name)
        if len(self.uasset.exports)!=1:
            raise RuntimeError('Unexpected number of exports')
        #name_list = uasset.name_list
        with open(uasset_name, 'rb') as f:
            self.uasset_size = get_size(f)

        with open(uexp_name, 'rb') as f:

            b = f.read(1)
            check(b, b'\x03')
            l=b''
            s=0
            b=f.read(1)
            while (b!=b'\x03' and b!=b'\x05'):
                b2 = f.read(1)
                l=b''.join([l, b, b2])

                s+=int(b[0])
                b = f.read(1)

            self.b=b

            s+=int(b[0])-3
            
            self.head=l
            self.original_width = read_uint32(f)
            self.original_height = read_uint32(f)
            self.id = f.read(16)
            self.unk = f.read(s//2)
            null = f.read(3)
            check(null, b'\x00'*3)
            unk = read_uint16_array(f, len=4)
            check(unk, [1,1,1,0])
            self.type_name_id = read_uint32(f)
            read_null(f)
            end_offset = read_uint32(f) #Offset to end of uexp?
            self.max_width = read_uint32(f)
            self.max_height = read_uint32(f)
            one = read_uint16(f)
            check(one, 1)
            ubulk_flag = read_uint16(f) #ubulk flag?
            check(ubulk_flag, UBULK_FLAG[self.has_ubulk])
            
            self.type = read_str(f)
            #check(self.type, name_list[self.type_name_id])

            if self.has_ubulk:
                read_null(f)
                read_null(f)
                self.ubulk_map_num = read_uint32(f) #bulk map num?
            else:
                self.ubulk_map_num = 0

            read_null(f)
            map_num = read_uint32(f) #map num ?
            self.uexp_map_num=map_num-self.ubulk_map_num
            
            #mip map data
            read_const_uint32(f, 1) #Entry Indicator?
            read_const_uint32(f, 64) #?
            uexp_map_size = read_uint32(f) #Length of Mipmap Data?
            read_const_uint32(f, uexp_map_size)
            self.offset = read_uint32(f) #Offset to start of Mipmap Data
            read_null(f)
            check(self.offset, self.uasset_size+f.tell())
            self.uexp_map_data = f.read(uexp_map_size)
            self.uexp_max_width=read_uint32(f)
            self.uexp_max_height=read_uint32(f)
            read_const_uint32(f, 1)
            read_const_uint32(f, self.uexp_map_num)

            #mip map meta data
            if self.has_ubulk:
                self.ubulk_map_meta = [MipmapMetadata.read(f, uexp=False) for i in range(self.ubulk_map_num)]
            self.uexp_map_meta = [MipmapMetadata.read(f, uexp=True) for i in range(self.uexp_map_num)]

            
            self.none_name_id = read_uint32(f)
            #check(name_list[self.none_name_id], 'None')
            #check(self.unk4, self.unk3-2-self.has_ubulk)
            read_null(f)
            foot=f.read()

            check(foot, UNREAL_SIGNATURE)
            check(f.tell()+self.uasset_size-12, end_offset)

        if self.has_ubulk:
            with open(ubulk_name, 'rb') as f:
                size = get_size(f)
                self.ubulk_data = [f.read(meta.data_size) for meta in self.ubulk_map_meta]
                check(size, f.tell())
        
        pixel_num=0
        for meta in self.uexp_map_meta:
            pixel_num += meta.pixel_num
        
        self.size_per_pixel = len(self.uexp_map_data)/pixel_num
        self.uexp_map_data_list = []
        i=0
        for meta in self.uexp_map_meta:
            size = int(meta.pixel_num*self.size_per_pixel)
            self.uexp_map_data_list.append(self.uexp_map_data[i:i+size])
            i+=size
        check(i, len(self.uexp_map_data))
        
        if self.type not in PF_FORMAT:
            raise RuntimeError('Unsupported format. ({})'.format(self.type))
        self.format_name = PF_FORMAT[self.type]
        check(self.size_per_pixel, BYTE_PER_PIXEL[self.format_name])

        print('load: ' + uasset_name)
        self.print(verbose)

    def get_max_size(self):
        if self.has_ubulk:
            meta = self.ubulk_map_meta
        else:
            meta = self.uexp_map_meta
        max_width=meta[0].width
        max_height=meta[0].height
        return max_width, max_height

    def get_mipmap_num(self):
        uexp_map_num = len(self.uexp_map_meta)      
        if self.has_ubulk:
            ubulk_map_num = len(self.ubulk_map_meta)
        else:
            ubulk_map_num = 0
        return uexp_map_num, ubulk_map_num

    def save(self, file):
        uasset_name, uexp_name, ubulk_name = get_all_file_path(file)
        if not self.has_ubulk:
            ubulk_name = None
        
        uexp_map_data_size = 0
        for d in self.uexp_map_data_list:
            uexp_map_data_size += len(d)

        uexp_map_num, ubulk_map_num = self.get_mipmap_num()

        with open(uexp_name, 'wb') as f:
            f.write(b'\x03')
            f.write(self.head)
            f.write(self.b)

            max_width, max_height = self.get_max_size()

            write_uint32(f, max_width)
            write_uint32(f, max_height)
            f.write(self.id)
            f.write(self.unk)
            f.write(b'\x00'*3)
            write_uint16_array(f, [1,1,1,0])
            write_uint32(f, self.type_name_id)
            write_null(f)

            new_end_offset = self.offset + uexp_map_data_size + uexp_map_num*32 + 16
            if self.has_ubulk:
                new_end_offset += ubulk_map_num*32
            write_uint32(f, new_end_offset)
            
            write_uint32(f, max_width)
            write_uint32(f, max_height)
            write_uint16(f, 1)
            write_uint16(f, UBULK_FLAG[self.has_ubulk])
            write_str(f, self.type)

            if self.has_ubulk:
                write_null(f)
                write_null(f)
                write_uint32(f, ubulk_map_num)
            
            write_null(f)
            write_uint32(f, uexp_map_num + ubulk_map_num)

            write_uint32(f, 1)
            write_uint32(f, 64)
            write_uint32(f, uexp_map_data_size)
            write_uint32(f, uexp_map_data_size)
            write_uint32(f, self.offset)
            write_null(f)

            for d in self.uexp_map_data_list:
                f.write(d)

            meta = self.uexp_map_meta
            max_width=meta[0].width
            max_height=meta[0].height
            write_uint32(f, max_width)
            write_uint32(f, max_height)

            write_uint32(f, 1)
            write_uint32(f, uexp_map_num)

            #mip map meta data
            if self.has_ubulk:
                for meta in self.ubulk_map_meta:
                    meta.write(f, self.uasset_size)

            for meta in self.uexp_map_meta:
                meta.write(f, self.uasset_size)

            write_uint32(f, self.none_name_id)
            write_null(f)
            f.write(UNREAL_SIGNATURE)
            size = f.tell()

        if self.has_ubulk:
            with open(ubulk_name, 'wb') as f:
                for data in self.ubulk_data:
                    f.write(data)

        
        self.uasset.exports[0].update(size -4, self.uasset_size)
        self.uasset.save(uasset_name, size)
        return uasset_name, uexp_name, ubulk_name


    def unlink_ubulk(self):
        if not self.has_ubulk:
            return
        self.offset-=12
        self.has_ubulk=False
        self.ubulk_map_num=0
        print('ubulk has been unlinked.')

    def remove_some_uexp_mipmaps(self):
        self.uexp_map_data_list=self.uexp_map_data_list[3:]
        self.uexp_map_meta= self.uexp_map_meta[3:]

    def remove_low_res_mipmaps(self):
        uexp_map_num, ubulk_map_num = self.get_mipmap_num()
        old_mipmap_num = uexp_map_num + ubulk_map_num

        if self.has_ubulk:
            self.uexp_map_data_list = [self.ubulk_data[0]]
            self.uexp_map_meta = [self.ubulk_map_meta[0]]
            self.uexp_map_meta[0].to_uexp()
        else:
            self.uexp_map_data_list=[self.uexp_map_data_list[0]]
            self.uexp_map_meta=[self.uexp_map_meta[0]]

        self.unlink_ubulk()
        print('mipmaps have been removed.')
        print('  mipmap: {} -> 1'.format(old_mipmap_num))

    def inject_dds(self, dds):
        if dds.format_name.split('(')[0] not in self.format_name:
            raise RuntimeError('The format does not match. ({}, {})'.format(self.type, dds.format_name))
        
        max_width, max_height = self.get_max_size()
        old_size = (max_width, max_height)
        uexp_map_num, ubulk_map_num = self.get_mipmap_num()
        old_mipmap_num = uexp_map_num + ubulk_map_num

        offset=0
        self.ubulk_map_meta=[]
        self.ubulk_data=[]
        self.uexp_map_data_list=[]
        self.uexp_map_meta=[]
        i=0
        for data, size in zip(dds.mipmap_data, dds.mipmap_size):
            if self.has_ubulk and i+1<len(dds.mipmap_data) and size[0]*size[1]>=1024**2:
                meta = MipmapMetadata(len(data), offset, size, False)
                offset+=len(data)
                self.ubulk_map_meta.append(meta)
                self.ubulk_data.append(data)
            else:
                meta = MipmapMetadata(0,0,size,True)
                self.uexp_map_data_list.append(data)
                self.uexp_map_meta.append(meta)
            i+=1

        if len(self.ubulk_map_meta)==0:
            self.has_ubulk=False

        max_width, max_height = self.get_max_size()
        new_size = (max_width, max_height)
        uexp_map_num, ubulk_map_num = self.get_mipmap_num()
        new_mipmap_num = uexp_map_num + ubulk_map_num

        print('dds has been injected.')
        print('  size: {} -> {}'.format(old_size, new_size))
        print('  mipmap: {} -> {}'.format(old_mipmap_num, new_mipmap_num))
        if dds.format_name=='BC6H(signed)':
            print('Warning: UE4 requires BC6H(unsigned) but your dds is BC6H(signed).')
        if new_mipmap_num>1 and (not is_power_of_2(max_width) or not is_power_of_2(max_height)):
            print('Warning: Mipmaps should have power of 2 as its width and height. ({}, {})'.format(self.width, self.height))
            

    def print(self, verbose=False):
        if verbose:
            i=0
            if self.has_ubulk:
                for meta in self.ubulk_map_meta:
                    print('  Mipmap {}'.format(i))
                    meta.print(padding=4)
                    i+=1
            for meta in self.uexp_map_meta:
                print('  Mipmap {}'.format(i))
                meta.print(padding=4)
                i+=1

        #print('  head: {}'.format(self.head))
        print('  original_width: {}'.format(self.original_width))
        print('  original_height: {}'.format(self.original_height))
        #print('  id: {}'.format(self.id))
        #print('  unk: {}'.format(self.unk))
        #print('  max width: {}'.format(self.max_width))
        #print('  max height: {}'.format(self.max_height))
        print('  type: {}'.format(self.type))
        #print('  number of ubulk\'s mip maps: {}'.format(self.ubulk_map_num))
        print('  number of mip maps: {}'.format(self.uexp_map_num + self.ubulk_map_num))
        #print('  size of mip map data in uexp: {}'.format(len(self.uexp_map_data)))
        #print('  texture data offset: {}'.format(self.offset))
        #print('  uexp max width: {}'.format(self.uexp_max_width))
        #print('  uexp max height: {}'.format(self.uexp_max_height))
        #print('  number of uexp\'s mip maps: {}'.format(self.uexp_map_num))
