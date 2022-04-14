import os
import shutil
import glob

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from kaapana.operators.HelperCaching import update_job
from kaapana.blueprints.kaapana_utils import get_operator_properties

class LocalWorkflowCleanerOperator(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):

        run_id, dag_run_dir, dag_run, downstream_tasks = get_operator_properties(**kwargs)
        conf = dag_run.conf

        if conf is not None and 'federated_form' in conf and conf['federated_form'] is not None:
            federated = conf['federated_form']
            if 'from_previous_dag_run' in federated and federated['from_previous_dag_run'] is not None:
                from_previous_dag_run_dir = os.path.join(WORKFLOW_DIR, conf['federated_form']['from_previous_dag_run'])
                print(f'Removing batch files from from_previous_dag_run: {from_previous_dag_run_dir}')
                if os.path.isdir(from_previous_dag_run_dir):
                    shutil.rmtree(from_previous_dag_run_dir)

        run_dir = dag_run_dir if self.run_dir is None else self.run_dir
        if self.clean_workflow_dir is True and (os.path.exists(run_dir)):
            print(("Cleaning dir: %s" % run_dir))
            shutil.rmtree(run_dir)
        if conf is not None and 'client_job_id' in conf:
            update_job(conf['client_job_id'], status='finished', run_id=dag_run.run_id, description=f'Finished successfully')

    def __init__(self,
                 dag,
                 run_dir=None,
                 clean_workflow_dir=True,
                 **kwargs):

        self.run_dir = run_dir
        self.clean_workflow_dir = clean_workflow_dir

        super().__init__(
            dag=dag,
            name="workflow-cleaner",
            python_callable=self.start,
            **kwargs
        )
