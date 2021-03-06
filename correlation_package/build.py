import sys
sys.path = ['', '/home/mongsil/anaconda3/envs/torch040/lib/python36.zip', '/home/mongsil/anaconda3/envs/torch040/lib/python3.6', '/home/mongsil/anaconda3/envs/torch040/lib/python3.6/lib-dynload', '/home/mongsil/anaconda3/envs/torch040/lib/python3.6/site-packages']
print(sys.version_info)
print(sys.path)

import os
import torch
import torch.utils.ffi

this_folder = os.path.dirname(os.path.abspath(__file__)) + '/'

Headers = []
Sources = []
Defines = []
Objects = []

if torch.cuda.is_available() == True:
    Headers += ['src/correlation_cuda.h']
    Sources += ['src/correlation_cuda.c']
    Defines += [('WITH_CUDA', None)]
    Objects += ['src/correlation_cuda_kernel.o']

ffi = torch.utils.ffi.create_extension(
    name='_ext.correlation',
    headers=Headers,
    sources=Sources,
    verbose=False,
    with_cuda=True,
    package=False,
    relative_to=this_folder,
    define_macros=Defines,
    extra_objects=[os.path.join(this_folder, Object) for Object in Objects]
)

if __name__ == '__main__':
    ffi.build()
