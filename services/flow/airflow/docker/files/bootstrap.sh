#!/usr/bin/env bash
#
#  Licensed to the Apache Software Foundation (ASF) under one   *
#  or more contributor license agreements.  See the NOTICE file *
#  distributed with this work for additional information        *
#  regarding copyright ownership.  The ASF licenses this file   *
#  to you under the Apache License, Version 2.0 (the            *
#  "License"); you may not use this file except in compliance   *
#  with the License.  You may obtain a copy of the License at   *
#                                                               *
#    http://www.apache.org/licenses/LICENSE-2.0                 *
#                                                               *
#  Unless required by applicable law or agreed to in writing,   *
#  software distributed under the License is distributed on an  *
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY       *
#  KIND, either express or implied.  See the License for the    *
#  specific language governing permissions and limitations      *
#  under the License.                                           *

# launch the appropriate process

if [ "$1" = "init" ]
then
	echo ""
	echo "Airflow init DB..."
	echo ""
	airflow db init || { echo 'ERROR: airflow initdb' ; exit 1; }
	airflow db upgrade || { echo 'ERROR: airflow db upgrade' ; exit 1; }
	echo "DONE"
fi

if [ "$1" = "webserver" ]
then
	exec airflow webserver
fi

if [ "$1" = "scheduler" ]
then
	exec airflow scheduler
fi
