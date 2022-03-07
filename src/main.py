import os, argparse, shutil
from io_util import mkdir, compare
from texture_asset import TextureUasset, get_all_file_path
from dds import DDS

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='.uasset, .uexp, .ubulk, or a folder')
    parser.add_argument('--save_folder', default='output', type=str, help='save folder')    
    parser.add_argument('--mode', default='parse', type=str, help='valid, parse, copy_uasset, inject, or remove_mipmaps')    
    args = parser.parse_args()
    return args

def parse(file, save_folder, clear=True):
    if file[-3:]=='dds':
        dds = DDS.load(file, verbose=True)
        #mkdir('workspace/header')
        #dds.save('workspace/header/'+dds.format_name.split('/')[0]+'.bin', only_header=True)
    else:
        TextureUasset(file, verbose=True)

def valid(file, save_folder, clear=True):
    folder = 'workspace/valid'
    mkdir(folder)
    if file[-3:]=='dds':
        dds = DDS.load(file)
        new_file=os.path.join(folder, os.path.basename(file))
        dds.save(new_file)
        compare(file, new_file)
        os.remove(new_file)
    else:
        uasset_name, uexp_name, ubulk_name = get_all_file_path(file)
        texture = TextureUasset(file, verbose=True)
        new_file=os.path.join(folder, os.path.basename(file))
        new_uasset_name, new_uexp_name, new_ubulk_name = texture.save(new_file)
        compare(uasset_name, new_uasset_name)
        compare(uexp_name, new_uexp_name)
        os.remove(new_uasset_name)
        os.remove(new_uexp_name)
        if new_ubulk_name is not None:
            compare(ubulk_name, new_ubulk_name)
            os.remove(new_ubulk_name)
    print('clear: {}'.format(folder))

def copy_uasset(file, save_folder, clear=True):
    folder = 'workspace/uasset'
    TextureUasset(file)
    if clear and os.path.exists(folder):
        shutil.rmtree(folder)
        print('clear: {}'.format(folder))

    mkdir(folder)
    uasset_name, uexp_name, ubulk_name = get_all_file_path(file)
    new_uasset_name, new_uexp_name, new_ubulk_name = get_all_file_path(file, rebase=True, folder=folder)
    shutil.copy(uasset_name, new_uasset_name)
    shutil.copy(uexp_name, new_uexp_name)
    print('copy: {} -> {}'.format(uasset_name, new_uasset_name))
    print('copy: {} -> {}'.format(uexp_name, new_uexp_name))
    if os.path.exists(ubulk_name):
        shutil.copy(ubulk_name, new_ubulk_name)
        print('copy: {} -> {}'.format(ubulk_name, new_ubulk_name))


def inject_dds(file, save_folder, clear=True):
    print(file)
    uasset_folder = 'workspace/uasset'
    if not os.path.exists(uasset_folder):
        raise RuntimeError('Uasset Not Found.')
    file_list = os.listdir(uasset_folder)
    uexp_list=[]
    for f in file_list:
        if f[-4:]=='uexp':
            uexp_list.append(f)

    if len(uexp_list)==0:
        raise RuntimeError('Uasset Not Found.')
    elif len(uexp_list)==1:
        uasset_base=uexp_list[0]
    else:
        dds_base = os.path.splitext(os.path.basename(file))[0]
        if dds_base+'.uexp' not in uexp_list:
            raise RuntimeError('The same name asset as dds not found. {}'.format(dds_base))
        id = uexp_list.index(dds_base+'.uexp')
        if id<0:
            raise RuntimeError('Uasset Not Found ({})'.format(os.path.join(uasset_folder, dds_base+'.uexp')))
        uasset_base=uexp_list[id]

    uasset_file = os.path.join(uasset_folder, uasset_base)
    texture = TextureUasset(uasset_file)
    dds = DDS.load(file)
    texture.inject_dds(dds)
    mkdir(save_folder)
    new_file = os.path.join(save_folder, os.path.basename(uasset_file))
    texture.save(new_file)

def export_as_dds(file, save_folder, clear=True):
    texture = TextureUasset(file)
    dds = DDS.asset_to_DDS(texture)
    mkdir(save_folder)
    new_file=os.path.splitext(os.path.join(save_folder, os.path.basename(file)))[0]+'.dds'
    dds.save(new_file)

def remove_mipmaps(file, save_folder, clear=True):
    mkdir(save_folder)
    texture = TextureUasset(file)
    texture.remove_mipmaps()
    new_file=os.path.join(save_folder, os.path.basename(file))
    texture.save(new_file)


if __name__=='__main__':
    args = get_args()
    file = args.file
    save_folder = args.save_folder
    mode = args.mode

    try:
        if mode=='valid':
            func = valid
        elif mode=='copy_uasset':
            func = copy_uasset
        elif mode=='inject':
            func = inject_dds
        elif mode=='remove_mipmaps':
            func = remove_mipmaps
        elif mode=='parse':
            func = parse
        elif mode=='export':
            func = export_as_dds
        else:
            raise RuntimeError('Unsupported mode. {}'.format(mode))
        
        if os.path.isfile(file):
            func(file, save_folder)
        else:
            folder = file
            clear=True
            for f in sorted(os.listdir(folder)):
                file = os.path.join(folder, f)

                if os.path.isfile(file) and (f[-4:]=='uexp' or f[-3:]=='dds'):
                    func(file, save_folder, clear=clear)
                    clear=False
    except Exception as e:
        print('Error: {}'.format(e))
        raise RuntimeError(e)
    print('Success!')

