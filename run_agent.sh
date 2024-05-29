if test -d learning_agent; then
  echo "Removing previous agent build"
  rm -r learning_agent
fi

find . -empty -type d -delete  # remove empty directories to avoid wrong hashes
autonomy packages lock
autonomy fetch --local --agent valory/learning_agent

source .env
python scripts/aea-config-replace.py

cd learning_agent

cp $PWD/../ethereum_private_key.txt .
autonomy add-key ethereum ethereum_private_key.txt
autonomy issue-certificates
aea -s run