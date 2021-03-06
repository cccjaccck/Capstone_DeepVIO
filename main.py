import torch
import torch.nn as nn
from torch.autograd import Variable
import torch.nn.functional as F
import torch.utils.data
import torch.optim as optim

from tensorboardX import SummaryWriter

import os
from utils import tools
from utils import se3qua

import FlowNetC
import csv
from PIL import Image
import numpy as np

import flowlib

from PIL import Image

import time


class Data:

    def __init__(self, base_dir, sequence):
        self.base_dir = base_dir
        self.sequence = sequence
        self.base_path_img = self.base_dir + self.sequence + '/img/'

        self.data_files = list(filter(lambda x: x[6] == "0", os.listdir(self.base_dir + self.sequence + '/img')))
        self.data_files = sorted(self.data_files, key=lambda x: int(x[8:-4]))
        # self.data_files = os.listdir(self.base_dir + self.sequence + '/img/')
        # self.data_files=sorted(self.data_files, key=lambda x:int(x[0:-4]))

        ## relative camera pose
        self.trajectory_relative = self.read_R6TrajFile('/sampled_relative_R6.txt')

        ##### cut the image sequence length
        self.time_length = self.trajectory_relative.shape[0]
        print(self.time_length, len(self.data_files))
        self.data_files = self.data_files[:self.time_length]
        print(self.time_length, len(self.data_files))

        ## abosolute camera pose (global)
        self.trajectory_abs = self.readTrajectoryFile('/groundtruth.txt')

        ## imu
        self.imu = self.readIMU_File('/imu.txt')

        self.imu_seq_len = 5

    # This is for groundtruth.txt read and
    # data structure is [tx ty tz qx qy qz qw]
    def readTrajectoryFile(self, path):
        # traj = []
        # with open(self.base_dir + self.sequence + path) as csvfile:
        #     spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
        #     for row in spamreader:
        #         parsed = [float(row[0]), float(row[1]), float(row[2]), float(row[3]),
        #                   float(row[4]), float(row[5]), float(row[6]), float(row[7])]
        #         traj.append(parsed[1:])
        #
        # print(row)
        # return np.array(traj)

        traj = []
        count = 0
        with open(self.base_dir + self.sequence + path) as data:
            for line in data.readlines():
                row = line.strip().split(' ')
                if count == 0:
                    count += 1
                    continue
                parsed = [float(row[0]), float(row[1]), float(row[2]),
                          float(row[3]), float(row[4]), float(row[5]), float(row[6]), float(row[7])]
                traj.append(parsed[1:])
        return np.array(traj)

    def read_R6TrajFile(self, path):
        traj = []
        with open(self.base_dir + self.sequence + path) as csvfile:
            spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
            for row in spamreader:
                parsed = [float(row[1]), float(row[2]), float(row[3]),
                          float(row[4]), float(row[5]), float(row[6])]
                traj.append(parsed)

        return np.array(traj)

        # traj = []
        # with open(self.base_dir + self.sequence + path) as csvfile:
        #     spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
        #     for row in spamreader:
        #         parsed = [float(row[1]), float(row[2]), float(row[3]),
        #                   float(row[4]), float(row[5]), float(row[6])]
        #         traj.append(parsed)
        #
        # return np.array(traj)

    # This is for imu.txt read and
    # data structure is [ang_vel_x, ang_vel_y, ang_vel_z, lin_ac_x, lin_acc_y, lin_acc_z]
    def readIMU_File(self, path):
        # imu = []
        # count = 0
        # with open(self.base_dir + self.sequence + path) as csvfile:
        #     spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
        #     for row in spamreader:
        #         if count == 0:
        #             count += 1
        #             continue
        #         parsed = [float(row[1]), float(row[2]), float(row[3]),
        #                   float(row[4]), float(row[5]), float(row[6])]
        #         imu.append(parsed)
        #
        # return np.array(imu)

        imu = []
        count = 0
        with open(self.base_dir + self.sequence + path) as data:

            for line in data.readlines():
                row = line.strip().split(' ')
                if count == 0:
                    count += 1
                    continue
                parsed = [float(row[1]), float(row[2]), float(row[3]),
                          float(row[4]), float(row[5]), float(row[6])]
                imu.append(parsed)
        return np.array(imu)

    def getTrajectoryAbs(self, idx):
        return self.trajectory_abs[idx]

    def getTrajectoryAbsAll(self):
        return self.trajectory_abs

    # get total imu data
    def getIMU(self):
        return self.imu

    def getDatafiles(self):
        return self.data_files

    def __len__(self):
        return len(self.trajectory_relative)

    def load_img_bat(self, idx, batch):
        batch_x = []
        batch_imu = []
        for i in range(batch):
            x_data_np_1 = np.array(Image.open(self.base_path_img + self.data_files[idx + i]))
            print(x_data_np_1.shape)
            x_data_np_2 = np.array(Image.open(self.base_path_img + self.data_files[idx + 1 + i]))
            print(x_data_np_2.shape)  # (w, h)

            ## 3 channels 여기 유로씨 데이터가 흑백이라 그냥 3채널 만들어 주나바 ㅠㅠ
            x_data_np_1 = np.array([x_data_np_1, x_data_np_1, x_data_np_1])
            x_data_np_2 = np.array([x_data_np_2, x_data_np_2, x_data_np_2])
            print(x_data_np_1.shape)
            # X = np.array([x_data_np_1, x_data_np_2])
            # batch_x.append(X)

            X = np.concatenate([x_data_np_1, x_data_np_2], axis=0)
            X = np.expand_dims(X, axis=0)
            print("X", X.shape)
            batch_x.append(X)
            print(len(batch_x))

            tmp = np.array(self.imu[idx - self.imu_seq_len + 1 + i:idx + 1 + i])
            batch_imu.append(tmp)

        batch_x = np.array(batch_x)
        batch_imu = np.array(batch_imu)
        print(batch_x.shape)
        print(batch_imu.shape)

        X = Variable(torch.from_numpy(batch_x).type(torch.FloatTensor).cuda())  # torch.Size([1, 2, 3, 480, 752])
        X2 = Variable(torch.from_numpy(batch_imu).type(torch.FloatTensor).cuda())

        ## F2F gt
        Y = Variable(torch.from_numpy(self.trajectory_relative[idx + 1:idx + 1 + batch]).type(torch.FloatTensor).cuda())

        ## global pose gt
        Y2 = Variable(torch.from_numpy(self.trajectory_abs[idx + 1:idx + 1 + batch]).type(torch.FloatTensor).cuda())

        return X, X2, Y, Y2


class Vinet(nn.Module):
    def __init__(self):
        super(Vinet, self).__init__()
        print("initing")
        self.rnn = nn.LSTM(
            input_size=49165,  # , 49165 # 49152,#24576,
            hidden_size=1024,  # 64,
            num_layers=2,
            batch_first=True)
        self.rnn.cuda()

        self.rnnIMU = nn.LSTM(
            input_size=6,
            hidden_size=6,
            num_layers=2,
            batch_first=True)
        self.rnnIMU.cuda()

        self.linear1 = nn.Linear(1024, 128)
        self.linear2 = nn.Linear(128, 6)
        # self.linear3 = nn.Linear(128, 6)
        self.linear1.cuda()
        self.linear2.cuda()
        # self.linear3.cuda()

        checkpoint = None
        checkpoint_pytorch = '/home/mongsil/workspace/build_ws_tf114/VINet/model/FlowNet2-C_checkpoint.pth.tar'
        # checkpoint_pytorch = '/notebooks/data/model/FlowNet2-SD_checkpoint.pth.tar'
        if os.path.isfile(checkpoint_pytorch):
            checkpoint = torch.load(checkpoint_pytorch, \
                                    map_location=lambda storage, loc: storage.cuda(0))
            best_err = checkpoint['best_EPE']
        else:
            print('No checkpoint')

        self.flownet_c = FlowNetC.FlowNetC(batchNorm=False)
        self.flownet_c.load_state_dict(checkpoint['state_dict'])
        self.flownet_c.cuda()

    def forward(self, image, imu, xyzQ):
        batch_size, timesteps, C, H, W = image.size()
        print("batch_size, timesteps, C, H, W : ", batch_size, timesteps, C, H, W)

        ## Input1: Feed image pairs to FlownetC
        c_in = image.view(batch_size, timesteps * C, H, W)
        print('c_in', c_in.shape)
        c_out = self.flownet_c(c_in)
        print('c_out', c_out.shape)

        ## Input2: Feed IMU records to LSTM
        imu_out, (imu_n, imu_c) = self.rnnIMU(imu)
        imu_out = imu_out[:, -1, :]
        print('imu_out', imu_out.shape)
        imu_out = imu_out.unsqueeze(1)
        print('imu_out', imu_out.shape)

        ## Combine the output of input1 and 2 and feed it to LSTM
        r_in = c_out.view(batch_size, timesteps, -1)
        # r_in = c_out.view(batch_size, 1, -1)
        print('r_in', r_in.shape)

        cat_out = torch.cat((r_in, imu_out), 2)  # 1 1 49158
        print(cat_out.shape)
        cat_out = torch.cat((cat_out, xyzQ), 2)  # 1 1 49165
        print(cat_out.shape)

        r_out, (h_n, h_c) = self.rnn(cat_out)
        l_out1 = self.linear1(r_out[:, -1, :])
        l_out2 = self.linear2(l_out1)
        # l_out3 = self.linear3(l_out2)

        return l_out2


def train(base_dir='/home/mongsil/workspace/datasets/', dataset_name='UZH'):
    base_dir = base_dir + dataset_name
    epoch = 1
    batch = 1
    model = Vinet()
    optimizer = optim.SGD(model.parameters(), lr=0.001, momentum=0.9)
    # optimizer = optim.Adam(model.parameters(), lr = 0.001)

    writer = SummaryWriter()

    model.train()

    dataset = Data(base_dir, '/indoor_forward_3_snapdragon_with_gt')
    # criterion  = nn.MSELoss()
    criterion = nn.L1Loss(size_average=False)

    start = 5
    end = len(dataset) - batch
    batch_num = (end - start)  # / batch
    startT = time.time()
    abs_traj = None

    with tools.TimerBlock("Start training") as block:
        for k in range(epoch):
            for i in range(start, end):  # len(mydataset)-1):
                data, data_imu, target_f2f, target_global = dataset.load_img_bat(i, batch)
                data, data_imu, target_f2f, target_global = \
                    data.cuda(), data_imu.cuda(), target_f2f.cuda(), target_global.cuda()

                optimizer.zero_grad()

                if i == start:
                    ## load first SE3 pose xyzQuaternion
                    abs_traj = dataset.getTrajectoryAbs(start)

                    abs_traj_input = np.expand_dims(abs_traj, axis=0)
                    abs_traj_input = np.expand_dims(abs_traj_input, axis=0)
                    abs_traj_input = Variable(torch.from_numpy(abs_traj_input).type(torch.FloatTensor).cuda())

                ## Forward
                output = model(data, data_imu, abs_traj_input)

                ## Accumulate pose
                numarr = output.data.cpu().numpy()

                abs_traj = se3qua.accu(abs_traj, numarr)

                abs_traj_input = np.expand_dims(abs_traj, axis=0)
                abs_traj_input = np.expand_dims(abs_traj_input, axis=0)
                abs_traj_input = Variable(torch.from_numpy(abs_traj_input).type(torch.FloatTensor).cuda())

                ## (F2F loss) + (Global pose loss)
                ## Global pose: Full concatenated pose relative to the start of the sequence
                loss = criterion(output, target_f2f) + criterion(abs_traj_input, target_global)

                loss.backward()
                optimizer.step()

                avgTime = block.avg()
                remainingTime = int((batch_num * epoch - (i + batch_num * k)) * avgTime)
                rTime_str = "{:02d}:{:02d}:{:02d}".format(int(remainingTime / 60 // 60),
                                                          int(remainingTime // 60 % 60),
                                                          int(remainingTime % 60))

                block.log('Train Epoch: {}\t[{}/{} ({:.0f}%)]\tLoss: {:.6f}, TimeAvg: {:.4f}, Remaining: {}'.format(
                    k, i, batch_num,
                    100. * (i + batch_num * k) / (batch_num * epoch), loss.data[0], avgTime, rTime_str))

                writer.add_scalar('loss', loss.data[0], k * batch_num + i)

            check_str = 'checkpoint_{}.pt'.format(k)
            torch.save(model.state_dict(), check_str)

    # torch.save(model, 'vinet_v1_01.pt')
    # model.save_state_dict('vinet_v1_01.pt')
    torch.save(model.state_dict(), 'vinet_v1_01.pt')
    writer.export_scalars_to_json("./all_scalars.json")
    writer.close()


def main():
    base_dir = '/home/mongsil/workspace/datasets/' + 'UZH/'
    # data = Data('/home/ssy/workspace/myspace/VIONet/data/indoor_forward', '/indoor_forward_3')
    # data.readIMU_File('/imu.txt')
    # # print(data.getDatafiles()[-1])
    # # print(data.getDatafiles())
    # image = np.array(Image.open('/home/ssy/workspace/myspace/VIONet/data/indoor_forward'+'/indoor_forward_3'+'/img/image_0_2.png'))
    # print(image.shape)
    # image_2=np.array([image, image, image])
    # print(image_2.shape)
    # test()
    # data.readTrajectoryFile('/groundtruth.txt')
    # print(data.getTrajectoryAbs())
    # print(data.getTrajectoryAbsAll())
    train(dataset_name="UZH")


if __name__ == '__main__':
    main()
