for f in example_broken_link.txt example_link.txt
do
  if [ -h $f ]
  then
    rm $f
  fi
done

for f in example_file.txt test_*.json test_*.json.lock test_cronjob.txt
do
  if [ -e $f ]
  then
    rm $f
  fi
done

rm -r /eos/user/s/sixtadm/test_xboinc/*
rm -r /afs/cern.ch/user/s/sixtadm/public/test_xboinc/*
rm -r level1 level5_res

