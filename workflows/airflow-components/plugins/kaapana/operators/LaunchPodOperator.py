from datetime import timedelta, datetime
import os
import json
from kaapana.kubetools.volume_mount import VolumeMount
from kaapana.kubetools.volume import Volume
from kaapana.operators.KaapanaApplicationOperator import KaapanaApplicationOperator

class LaunchPodOperator(KaapanaApplicationOperator):

    def pre_execute(self, context):
        print("Starting moule LaunchPodOperator...")
        print(context)
        conf = context['dag_run'].conf
        print(conf)
        self.port = int(conf['port'])
        self.ingress_path = conf['ingress_path']
        self.image = conf['image']

        if 'image_pull_secrets' in conf:
            self.image_pull_secrets.append(conf['image_pull_secrets'])

        envs = {
            "INGRESS_PATH": self.ingress_path,
        }

        self.env_vars.update(envs)

        if 'envs' in conf:
            self.env_vars.update(conf['envs'])

        if 'args' in conf:
            self.arguments = conf['args']

        if 'cmds' in conf:
            self.cmds = conf['cmds']
        
        if 'annotations' in conf:
            self.annotations = conf['annotations']

        self.volume_mounts = []
        if 'volume_mounts' in conf:
            print('writing volume_mounts')
            for volume_mount in conf['volume_mounts']:
                print('Writing volume_mount', volume_mount)
                self.volume_mounts.append(
                    VolumeMount(**volume_mount)
                )

        self.volumes = []
        if 'volumes' in conf:
            for volume in conf['volumes']:
                print('as', volume)
                self.volumes.append(
                    Volume(**volume)
                )

    def __init__(self,
                 dag,
                 execution_timeout=timedelta(hours=12),
                 env_vars=None,
                 **kwargs
                 ):

        super().__init__(
            dag=dag,
            name='launch-pod',
            image_pull_secrets=["registry-secret"],
            service=True,
            ingress=True,
            execution_timeout=execution_timeout,
            startup_timeout_seconds=360, # 5min
            **kwargs)
