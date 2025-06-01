command to set up the jupyter notebook (all after create and activate the venv)

 pip install notebook
 pip install ipykernel
 python -m ipykernel install --user --name=venv --display-name "Python (venv)"




 how to load the database in docker 

danielguarnizo at MacBook-Air-Daniel in ~/workspace/Master/LLMs/GraphRAG (venv) 
$ docker-compose down
WARN[0000] /Users/danielguarnizo/workspace/Master/LLMs/GraphRAG/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
[+] Running 2/2
 ✔ Container neo4j-db        Removed                                                                                                                                            5.4s 
 ✔ Network graphrag_default  Removed                                                                                                                                            0.2s 
(base) 
danielguarnizo at MacBook-Air-Daniel in ~/workspace/Master/LLMs/GraphRAG (venv) 
$ rm -rf ./neo4j/data
(base) 
danielguarnizo at MacBook-Air-Daniel in ~/workspace/Master/LLMs/GraphRAG (venv) 
$ docker-compose up -d
WARN[0000] /Users/danielguarnizo/workspace/Master/LLMs/GraphRAG/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
[+] Running 2/2
 ✔ Network graphrag_default  Created                                                                                                                                            0.0s 
 ✔ Container neo4j-db        Started                                                                                                                                            0.1s 
(base) 
danielguarnizo at MacBook-Air-Daniel in ~/workspace/Master/LLMs/GraphRAG (venv) 
$ docker exec -it neo4j-db bash
root@d38efc6a4351:/var/lib/neo4j# neo4j-admin load --from=/var/lib/neo4j/import/healthcare-analytics-44.dump --database=neo4j --force
exit
Selecting JVM - Version:11.0.17+8, Name:OpenJDK 64-Bit Server VM, Vendor:Eclipse Adoptium
Done: 94 files, 22.89MiB processed.
exit

What's next:
    Try Docker Debug for seamless, persistent debugging tools in any container or image → docker debug neo4j-db
    Learn more at https://docs.docker.com/go/debug-cli/
(base) 
danielguarnizo at MacBook-Air-Daniel in ~/workspace/Master/LLMs/GraphRAG (venv) 
$ docker-compose restart
WARN[0000] /Users/danielguarnizo/workspace/Master/LLMs/GraphRAG/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
[+] Restarting 1/1
 ✔ Container neo4j-db  Started                                                                                                                                                  5.5s 
(base) 