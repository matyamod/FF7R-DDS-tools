import os
from io_util import *
from uasset import Uasset

BYTE_PER_PIXEL = {
    'DXT1/BC1': 0.5,
    'DXT5/BC3': 1,
    'BC4/ATI1': 0.5,
    'BC5/ATI2': 1,
    'BC6H(unsigned)': 1,
    'BC6H(signed)': 1,
    'BC7': 1,
    'FloatRGBA': 8,
    'B8G8R8A8(sRGB)': 4
}

PF_FORMAT = {
    'PF_DXT1': 'DXT1/BC1',
    'PF_DXT5': 'DXT5/BC3',
    'PF_BC4': 'BC4/ATI1',
    'PF_BC5': 'BC5/ATI2',
    'PF_BC6H': 'BC6H(unsigned)',
    'PF_BC7': 'BC7', 
    'PF_FloatRGBA': 'FloatRGBA',
    'PF_B8G8R8A8': 'B8G8R8A8(sRGB)'
}

def is_power_of_2(n):
    if n==1:
        return True
    if n%2!=0:
        return False
    return is_power_of_2(n//2)

EXT = ['.uasset', '.uexp', '.ubulk']
def get_all_file_path(file):
    base_name, ext = os.path.splitext(file)

    if ext not in EXT:
        raise RuntimeError('Not Uasset. ({})'.format(file))

    return [base_name + ext for ext in EXT]

#mipmap meta data (size, offset , etc.)
class MipmapMetadata:
    UEXP_FLAG=[66817, 32]
    def __init__(self, data_size, offset, size, uexp):
        self.uexp=uexp
        if uexp:
            self.data_size=0
        else:
            self.data_size=data_size
        self.offset=offset
        self.width=size[0]
        self.height=size[1]
        self.pixel_num = self.width*self.height

    def read(f):
        read_const_uint32(f, 1)    #Entry Indicator?
        flag = read_uint32(f)      #uexp flag (32:uexp, 66817:ubulk)
        uexp=flag==MipmapMetadata.UEXP_FLAG[1]
        data_size = read_uint32(f)
        if uexp:
            check(data_size, 0)
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
        self.data_size=0
        self.uexp=True

    def write(self, f, uasset_size):
        new_offset = f.tell() + uasset_size+24

        write_uint32(f, 1)
        write_uint32(f, MipmapMetadata.UEXP_FLAG[self.uexp])
        write_uint32(f, self.data_size)
        write_uint32(f, self.data_size)
        if self.uexp:
            write_uint32(f, new_offset)
        else:
            write_uint32(f, self.offset)
        write_null(f)

        write_uint32(f, self.width)
        write_uint32(f, self.height)

class TextureUasset:
    UNREAL_SIGNATURE = b'\xC1\x83\x2A\x9E'
    UBULK_FLAG = [0, 16384]
    
    def __init__(self, file_path, verbose=False):

        if not os.path.isfile(file_path):
            raise RuntimeError('Not File. ({})'.format(file_path))

        uasset_name, uexp_name, ubulk_name = get_all_file_path(file_path)

        self.uasset = Uasset(uasset_name)
        if len(self.uasset.exports)!=1:
            raise RuntimeError('Unexpected number of exports')

        with open(uasset_name, 'rb') as f:
            self.uasset_size = get_size(f)

        with open(uexp_name, 'rb') as f:

            f.read(1)
            b = f.read(1)
            while (b not in [b'\x03', b'\x05']):
                f.read(1)
                b = f.read(1)

            s = f.tell()
            f.seek(0)
            self.head=f.read(s)
            self.original_width = read_uint32(f)
            self.original_height = read_uint32(f)
            self.id = f.read(16)
            offset=f.tell()
            b = f.read(5)
            while (b!=b'\x00\x00\x00\x00\x01'):
                b=b''.join([b[1:], f.read(1)])
            s=f.tell()-offset-1
            f.seek(offset)
            self.unk = f.read(s)
            unk = read_uint16_array(f, len=4)
            check(unk, [1,1,1,0])
            self.type_name_id = read_uint32(f)
            read_null(f)
            end_offset = read_uint32(f) #Offset to end of uexp?
            self.max_width = read_uint32(f)
            self.max_height = read_uint32(f)
            one = read_uint16(f)
            check(one, 1)
            ubulk_flag = read_uint16(f) #ubulk flag (uexp:0, ubulk:16384)
            self.has_ubulk=ubulk_flag==TextureUasset.UBULK_FLAG[1]
            
            self.type = read_str(f)
            #check(self.type, name_list[self.type_name_id])

            if self.has_ubulk:
                read_null(f)
                read_null(f)
                self.ubulk_map_num = read_uint32(f) #bulk map num + unk_map_num
            else:
                self.ubulk_map_num = 0

            self.unk_map_num=read_uint32(f) #number of some mipmaps in uexp
            map_num = read_uint32(f) #map num ?
            self.ubulk_map_num-=self.unk_map_num
            self.uexp_map_num=map_num-self.ubulk_map_num

            
            #read mipmap data
            read_const_uint32(f, 1) #Entry Indicator?
            read_const_uint32(f, 64) #?
            uexp_map_size = read_uint32(f) #Length of Mipmap Data
            read_const_uint32(f, uexp_map_size)
            self.offset = read_uint32(f) #Offset to start of Mipmap Data
            read_null(f)
            check(self.offset, self.uasset_size+f.tell())
            uexp_map_data = f.read(uexp_map_size)
            self.uexp_max_width=read_uint32(f)
            self.uexp_max_height=read_uint32(f)
            read_const_uint32(f, 1)
            read_const_uint32(f, self.uexp_map_num)

            #read mipmap meta data
            if self.has_ubulk:
                self.ubulk_map_meta = [MipmapMetadata.read(f) for i in range(self.ubulk_map_num)]
            self.uexp_map_meta = [MipmapMetadata.read(f) for i in range(self.uexp_map_num)]

            self.none_name_id = read_uint32(f)
            read_null(f)
            foot=f.read()

            check(foot, TextureUasset.UNREAL_SIGNATURE)
            check(f.tell()+self.uasset_size-12, end_offset)

        #read ubulk
        if self.has_ubulk:
            with open(ubulk_name, 'rb') as f:
                size = get_size(f)
                self.ubulk_map_data = [f.read(meta.data_size) for meta in self.ubulk_map_meta]
                check(size, f.tell())

        #get format name
        if self.type not in PF_FORMAT:
            raise RuntimeError('Unsupported format. ({})'.format(self.type))
        self.format_name = PF_FORMAT[self.type]

        #pixel_num=0
        #for meta in self.uexp_map_meta:
        #    pixel_num += meta.pixel_num        
        #self.byte_per_pixel = len(uexp_map_data)/pixel_num        
        self.byte_per_pixel = BYTE_PER_PIXEL[self.format_name]

        #split mipmap data
        self.uexp_map_data = []
        i=0
        for meta in self.uexp_map_meta:
            size = int(meta.pixel_num*self.byte_per_pixel)
            self.uexp_map_data.append(uexp_map_data[i:i+size])
            i+=size
        check(i, len(uexp_map_data))
        
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
        folder = os.path.dirname(file)
        if folder not in ['.', ''] and not os.path.exists(folder):
            mkdir(folder)

        uasset_name, uexp_name, ubulk_name = get_all_file_path(file)
        if not self.has_ubulk:
            ubulk_name = None
        
        uexp_map_data_size = 0
        for d in self.uexp_map_data:
            uexp_map_data_size += len(d)

        uexp_map_num, ubulk_map_num = self.get_mipmap_num()

        with open(uexp_name, 'wb') as f:
            f.write(self.head)

            max_width, max_height = self.get_max_size()

            write_uint32(f, max_width)
            write_uint32(f, max_height)
            f.write(self.id)
            f.write(self.unk)
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
            write_uint16(f, TextureUasset.UBULK_FLAG[self.has_ubulk])
            write_str(f, self.type)

            if self.has_ubulk:
                write_null(f)
                write_null(f)
                write_uint32(f, ubulk_map_num+self.unk_map_num)
            
            write_uint32(f, self.unk_map_num)
            write_uint32(f, uexp_map_num + ubulk_map_num)

            write_uint32(f, 1)
            write_uint32(f, 64)
            write_uint32(f, uexp_map_data_size)
            write_uint32(f, uexp_map_data_size)
            write_uint32(f, self.offset)
            write_null(f)

            for d in self.uexp_map_data:
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
            f.write(TextureUasset.UNREAL_SIGNATURE)
            size = f.tell()

        if self.has_ubulk:
            with open(ubulk_name, 'wb') as f:
                for data in self.ubulk_map_data:
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

    def remove_mipmaps(self):
        uexp_map_num, ubulk_map_num = self.get_mipmap_num()
        old_mipmap_num = uexp_map_num + ubulk_map_num

        if self.has_ubulk:
            self.uexp_map_data = [self.ubulk_map_data[0]]
            self.uexp_map_meta = [self.ubulk_map_meta[0]]
            self.uexp_map_meta[0].to_uexp()
        else:
            self.uexp_map_data=[self.uexp_map_data[0]]
            self.uexp_map_meta=[self.uexp_map_meta[0]]

        self.unlink_ubulk()
        print('mipmaps have been removed.')
        print('  mipmap: {} -> 1'.format(old_mipmap_num))

    def inject_dds(self, dds):
        
        if dds.header.format_name.split('(')[0] not in self.format_name:
            raise RuntimeError('The format does not match. ({}, {})'.format(self.type, dds.header.format_name))
        
        max_width, max_height = self.get_max_size()
        old_size = (max_width, max_height)
        uexp_map_num, ubulk_map_num = self.get_mipmap_num()
        old_mipmap_num = uexp_map_num + ubulk_map_num

        offset=0
        self.ubulk_map_data=[]
        self.ubulk_map_meta=[]
        self.uexp_map_data=[]
        self.uexp_map_meta=[]
        i=0
        for data, size in zip(dds.mipmap_data, dds.mipmap_size):
            if self.has_ubulk and i+1<len(dds.mipmap_data) and size[0]*size[1]>=1024**2:
                meta = MipmapMetadata(len(data), offset, size, False)
                offset+=len(data)
                self.ubulk_map_meta.append(meta)
                self.ubulk_map_data.append(data)
            else:
                meta = MipmapMetadata(0,0,size,True)
                self.uexp_map_data.append(data)
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
        if dds.header.format_name=='BC6H(signed)':
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

        print('  original_width: {}'.format(self.original_width))
        print('  original_height: {}'.format(self.original_height))
        print('  format: {}'.format(self.type))
        print('  mipmap num: {}'.format(self.uexp_map_num + self.ubulk_map_num))
