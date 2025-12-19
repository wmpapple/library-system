pip install -r .\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
npm install @vue/composition-api --save-dev

docker-compose up -d
docker logs -f library_frontend
# frontend
conda activate dbs
cd frontend
npm run serve


# backend
uvicorn backend.app.main:app --reload

docker exec -it library_backend /bin/bash
ls app
python -m app.database