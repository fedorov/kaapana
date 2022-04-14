import os
import sys
from pathlib import Path
import uuid
import torch
import json
import pickle
import shutil
import collections
from torch.utils.tensorboard import SummaryWriter
from nnunet.training.model_restore import restore_model
from batchgenerators.utilities.file_and_folder_operations import join

sys.path.insert(0, '../')
sys.path.insert(0, '/executables')
from common.kaapana_federated.KaapanaFederatedTraining import KaapanaFederatedTrainingBase, requests_retry_session


class nnUNetFederatedTraining(KaapanaFederatedTrainingBase):

    @staticmethod
    def get_network_trainer(folder):
        checkpoint = join(folder, "model_final_checkpoint.model")
        pkl_file = checkpoint + ".pkl"
        return restore_model(pkl_file, checkpoint, False)

    def __init__(self, run_id=None, workflow_dir=None, federated_operators=None, skip_operators=None):
        super().__init__(workflow_dir)
        
        if self.remote_conf_data['workflow_form']['train_max_epochs'] % self.remote_conf_data['federated_form']['federated_total_rounds'] != 0:
            raise ValueError('train_max_epochs has to be multiple of federated_total_rounds')
        else:
            self.remote_conf_data['workflow_form']['epochs_per_round'] = int(self.remote_conf_data['workflow_form']['train_max_epochs'] / self.remote_conf_data['federated_form']['federated_total_rounds'])
        print(f"Overwriting prep_increment_step to to_dataset_properties!")

        self.remote_conf_data['workflow_form']['prep_increment_step'] = 'to_dataset_properties'
        # We increase the total federated round by one, because we need the final round to download the final model.
        # The nnUNet won't train an epoch longer, since its train_max_epochs!
        self.remote_conf_data['federated_form']['federated_total_rounds'] = self.remote_conf_data['federated_form']['federated_total_rounds'] + 1
        print(f"Epochs per round {self.remote_conf_data['workflow_form']['epochs_per_round']}")
        
    def tensorboard_logs(self, federated_round):
        current_federated_round_dir = Path(os.path.join(self.fl_working_dir, str(federated_round)))
        for instance_name, _ in self.tmp_federated_site_info.items():
            filename = current_federated_round_dir / instance_name / 'nnunet-training' / 'experiment_results.json'
            with open(filename) as json_file:
                exp_data = json.load(json_file)
            tensorboard_log_dir = Path(os.path.join('/minio', 'tensorboard', self.remote_conf_data["federated_form"]["federated_dir"], os.getenv('OPERATOR_OUT_DIR', 'federated-operator'), instance_name))
            if tensorboard_log_dir.is_dir():
                print('Removing previous logs, since we will write all logs again...')
                shutil.rmtree(tensorboard_log_dir)
            self.writer = SummaryWriter(log_dir=tensorboard_log_dir)
            for epoch_data in exp_data:
                for key, value in epoch_data.items():
                    if key != 'epoch' and key != 'fold':
                        self.writer.add_scalar(key, value, epoch_data['epoch'])
                
    def update_data(self, federated_round):     
        print(Path(os.path.join(self.fl_working_dir, str(federated_round))))
        
        if federated_round == -1:
            print('Preprocessing round!')
            preprocessing_path = Path(os.path.join(self.fl_working_dir, str(federated_round)))
            dataset_properties_files = []
            for idx, fname in enumerate(preprocessing_path.rglob('dataset_properties.pkl')):
                if 'nnUNet_cropped_data' in str(fname):
                    dataset_properties_files.append(fname)
                    if idx == 0:
                        with open(fname, 'rb') as f:
                            concat_dataset_properties = pickle.load(f)
                    else:
                        with open(fname, 'rb') as f:
                            dataset_properties = pickle.load(f)
                        for k in ['all_sizes', 'all_spacings']:
                            concat_dataset_properties[k] = concat_dataset_properties[k] + dataset_properties[k]
                        concat_dataset_properties['size_reductions'].update(dataset_properties['size_reductions'])
                        for k in ['all_classes', 'modalities', 'intensityproperties']:       
                            assert json.dumps(dataset_properties[k]) == json.dumps(concat_dataset_properties[k])
                    print(fname)
            print(concat_dataset_properties)
            for fname in dataset_properties_files:
                with open(fname, 'wb') as f:
                    pickle.dump(concat_dataset_properties, f)

            # Dummy creation of nnunet-training folder, because a tar is expected in the next round due
            # to from_previous_dag_run not None. Mybe there is a better solution for the future...
            for instance_name, tmp_site_info in self.tmp_federated_site_info.items():
                nnunet_training_file_path = tmp_site_info['file_paths'][0].replace('nnunet-preprocess', 'nnunet-training')
                nnunet_training_dir = nnunet_training_file_path.replace('.tar.gz', '')
                Path(nnunet_training_dir).mkdir(exist_ok=True)
                tmp_site_info['file_paths'].append(nnunet_training_file_path)
                nnunet_training_next_object_name = tmp_site_info['next_object_names'][0].replace('nnunet-preprocess', 'nnunet-training')
                tmp_site_info['next_object_names'].append(nnunet_training_next_object_name)
        else:
            print('Training mode')  
            self.tensorboard_logs(federated_round)
            models_path = Path(os.path.join(self.fl_working_dir, str(federated_round)))
            averaged_state_dict = collections.OrderedDict()
            averaged_amp_grad_scaler = dict()
            print('Loading averaged checkpoints')
            for idx, fname in enumerate(models_path.rglob('model_final_checkpoint.model')):
                print(fname)
                checkpoint = torch.load(fname, map_location=torch.device('cpu'))
                if idx==0:
                    for key, value in checkpoint['state_dict'].items():
                        averaged_state_dict[key] = value
                    if 'amp_grad_scaler' in checkpoint.keys():
                        for key, value in checkpoint['amp_grad_scaler'].items():
                            averaged_amp_grad_scaler[key] = value 
                else:
                    for key, value in checkpoint['state_dict'].items():
                        averaged_state_dict[key] =  (averaged_state_dict[key] + checkpoint['state_dict'][key]) / 2.
                    if 'amp_grad_scaler' in checkpoint.keys():
                        for key, value in checkpoint['amp_grad_scaler'].items():
                            averaged_amp_grad_scaler[key] = (averaged_amp_grad_scaler[key] + checkpoint['amp_grad_scaler'][key]) / 2.

            print('Saving averaged checkpoints')
            for idx, fname in enumerate(models_path.rglob('model_final_checkpoint.model')):
                print(fname)
                checkpoint['state_dict'] = averaged_state_dict
    #             if 'amp_grad_scaler' in checkpoint.keys():
    #                 checkpoint['amp_grad_scaler'] = averaged_amp_grad_scaler
                torch.save(checkpoint, fname)

    def on_train_step_end(self, federated_round):
        if federated_round == -1:
            print('Taking actions...')
            self.remote_conf_data['federated_form']['skip_operators'].remove('nnunet-training')
            self.remote_conf_data['workflow_form']['prep_increment_step'] = 'from_dataset_properties'
        else:
            if federated_round == 0:
                print('Removing nnunet-preprocess from federated_operators')
                self.remote_conf_data['federated_form']['federated_operators'].remove('nnunet-preprocess')
            self.remote_conf_data['workflow_form']['train_continue'] = True
        print(federated_round, self.remote_conf_data['federated_form']['federated_total_rounds'])

if __name__ == "__main__":
    kaapana_ft = nnUNetFederatedTraining()
    kaapana_ft.train_step(-1)
    kaapana_ft.train()

