
echo Start nightly RU build and test
cd /mnt/80GB/workarea/git/PHY5G_Rel/release_builder
source ru_cron_build.sh 2>&1 | tee nightly_build_test.log

