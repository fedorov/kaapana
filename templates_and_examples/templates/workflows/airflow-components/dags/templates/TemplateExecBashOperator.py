from datetime import timedelta


from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator, default_registry, default_project


class TemplateExecBashOperator(KaapanaBaseOperator):

    def __init__(self,
                 dag,
                 execution_timeout=timedelta(minutes=15),
                 *args, **kwargs
                 ):

        super().__init__(
            dag=dag,
            name='temp-exec-bash',
            image=f"{default_registry}/bash-template:0.1.0",
            image_pull_secrets=["registry-secret"],
            execution_timeout=execution_timeout,
            *args,
            **kwargs
        )
