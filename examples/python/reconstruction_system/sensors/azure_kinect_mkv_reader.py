# ----------------------------------------------------------------------------
# -                        Open3D: www.open3d.org                            -
# ----------------------------------------------------------------------------
# The MIT License (MIT)
#
# Copyright (c) 2018-2021 www.open3d.org
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
# ----------------------------------------------------------------------------

# examples/python/reconstruction_system/sensors/azure_kinect_mkv_reader.py

import argparse
import open3d as o3d
import os
import json
import sys

pwd = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(pwd, '..'))
from initialize_config import initialize_config


class ReaderWithCallback:

    def __init__(self, input, output):
        self.flag_exit = False
        self.flag_play = True
        self.flag_shot = False
        self.input = input
        self.output = output

        self.reader = o3d.io.AzureKinectMKVReader()
        self.reader.open(self.input)
        if not self.reader.is_opened():
            raise RuntimeError("Unable to open file {}".format(args.input))

    def escape_callback(self, vis):
        self.flag_exit = True
        return False

    def space_callback(self, vis):
        if self.flag_play:
            print('Playback paused, press [SPACE] to continue.')
        else:
            print('Playback resumed, press [SPACE] to pause.')
        self.flag_play = not self.flag_play
        return False
    
    def a_callback(self, vis):
        self.flag_shot = True
        return False

    def run(self):
        glfw_key_escape = 256
        glfw_key_space = 32
        glfw_key_a = 65
        vis = o3d.visualization.VisualizerWithKeyCallback()
        vis.register_key_callback(glfw_key_escape, self.escape_callback)
        vis.register_key_callback(glfw_key_space, self.space_callback)
        vis.register_key_callback(glfw_key_a, self.a_callback)

        vis_geometry_added = False
        vis.create_window('reader', 1920, 540)

        print(
            "MKV reader initialized. Press [SPACE] to pause/start, [ESC] to exit."
        )

        if self.output is not None:
            abspath = os.path.abspath(self.output)

            #color画像とdepth画像の保存
            # metadata = self.reader.get_metadata()
            # o3d.io.write_azure_kinect_mkv_metadata(
            #     '{}/intrinsic.json'.format(abspath), metadata)

            # config = {
            #     'path_dataset': abspath,
            #     'path_intrinsic': '{}/intrinsic.json'.format(abspath)
            # }
            # initialize_config(config)
            # with open('{}/config.json'.format(abspath), 'w') as f:
            #     json.dump(config, f, indent=4)

            #jsonファイルからintrinsicを読み込み
            metadata = self.reader.get_metadata()
            o3d.io.write_azure_kinect_mkv_metadata('{}/intrinsic.json'.format(abspath), metadata)
            json_open = open('{}/intrinsic.json'.format(abspath), 'r')
            json_load = json.load(json_open)
            json_open.close()
            phc = o3d.camera.PinholeCameraIntrinsic(json_load["width"], json_load["height"], 
                json_load["intrinsic_matrix"][0], json_load["intrinsic_matrix"][4], json_load["intrinsic_matrix"][6], json_load["intrinsic_matrix"][7])
        
        idx = 0
        while not self.reader.is_eof() and not self.flag_exit:
            if self.flag_play:
                rgbd = self.reader.next_frame()
                if rgbd is None:
                    continue
                
                #pcdデータ保存
                if self.flag_shot:
                    #next_frame()のままでは無理だったため、再度定義し直した
                    new_rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(rgbd.color, rgbd.depth, convert_rgb_to_intensity = False)
                    pcd = o3d.geometry.PointCloud.create_from_rgbd_image(new_rgbd, phc)
                    o3d.io.write_point_cloud("{0}/{1:05d}.pcd".format(abspath, idx), pcd)
                    print("Shot! {0:05d}.pcd".format(idx))
                    self.flag_shot = False
                idx += 1

                if not vis_geometry_added:
                    vis.add_geometry(rgbd)
                    vis_geometry_added = True

                #color画像とdepth画像の保存
                # if self.output is not None:
                #     color_filename = '{0}/color/{1:05d}.jpg'.format(
                #         self.output, idx)
                #     print('Writing to {}'.format(color_filename))
                #     o3d.io.write_image(color_filename, rgbd.color)

                #     depth_filename = '{0}/depth/{1:05d}.png'.format(
                #         self.output, idx)
                #     print('Writing to {}'.format(depth_filename))
                #     o3d.io.write_image(depth_filename, rgbd.depth)
                #     idx += 1

            try:
                vis.update_geometry(rgbd)
            except NameError:
                pass
            vis.poll_events()
            vis.update_renderer()

        self.reader.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Azure kinect mkv reader.')
    parser.add_argument('--input',
                        type=str,
                        required=True,
                        help='input mkv file')
    parser.add_argument('--output',
                        type=str,
                        help='output path to store color/ and depth/ images')
    args = parser.parse_args()

    if args.input is None:
        parser.print_help()
        exit()

    if args.output is None:
        print('No output path, only play mkv')
    elif os.path.isdir(args.output):
        print('Output path {} already existing, only play mkv'.format(
            args.output))
        args.output = None
    else:
        try:
            os.mkdir(args.output)
            #color画像とdepth画像の保存
            #os.mkdir('{}/color'.format(args.output))
            #os.mkdir('{}/depth'.format(args.output))
        except (PermissionError, FileExistsError):
            print('Unable to mkdir {}, only play mkv'.format(args.output))
            args.output = None

    reader = ReaderWithCallback(args.input, args.output)
    reader.run()
