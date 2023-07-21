#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
# LANG=en_US.UTF-8
is64bit=$(getconf LONG_BIT)

echo -e "您正在安装的是\033[31mmdserver-web测试版\033[0m，非开发测试用途请使用正式版 install.sh ！"
echo -e "You are installing\033[31m mdserver-web dev version\033[0m, normally use install.sh for production.\n"
sleep 1

{

	if [ -f /etc/motd ]; then
		echo "welcome to mdserver-web panel" >/etc/motd
	fi

	startTime=$(date +%s)

	_os=$(uname)
	echo "use system: ${_os}"

	if [ "$EUID" -ne 0 ]; then
		echo "Please run as root!"
		exit
	fi

	if [ ${_os} == "Darwin" ]; then
		OSNAME='macos'
	elif grep -Eq "openSUSE" /etc/*-release; then
		OSNAME='opensuse'
		zypper refresh
	elif grep -Eq "FreeBSD" /etc/*-release; then
		OSNAME='freebsd'
	elif grep -Eqi "CentOS" /etc/issue || grep -Eqi "CentOS" /etc/*-release; then
		OSNAME='rhel'
		yum install -y wget zip unzip
	elif grep -Eqi "Fedora" /etc/issue || grep -Eqi "Fedora" /etc/*-release; then
		OSNAME='rhel'
		yum install -y wget zip unzip
	elif grep -Eqi "Rocky" /etc/issue || grep -Eqi "Rocky" /etc/*-release; then
		OSNAME='rhel'
		yum install -y wget zip unzip
	elif grep -Eqi "AlmaLinux" /etc/issue || grep -Eqi "AlmaLinux" /etc/*-release; then
		OSNAME='rhel'
		yum install -y wget zip unzip
	elif grep -Eqi "Amazon Linux" /etc/issue || grep -Eqi "Amazon Linux" /etc/*-release; then
		OSNAME='amazon'
		yum install -y wget zip unzip
	elif grep -Eqi "Debian" /etc/issue || grep -Eqi "Debian" /etc/*-release; then
		OSNAME='debian'
		apt update -y
		apt install -y devscripts
		apt install -y wget zip unzip
	elif grep -Eqi "Ubuntu" /etc/issue || grep -Eqi "Ubuntu" /etc/*-release; then
		OSNAME='ubuntu'
		apt install -y wget zip unzip
	else
		OSNAME='unknow'
	fi

	# HTTP_PREFIX="https://"
	# LOCAL_ADDR=common
	# ping  -c 1 github.com > /dev/null 2>&1
	# if [ "$?" != "0" ];then
	# 	LOCAL_ADDR=cn
	# 	HTTP_PREFIX="https://ghproxy.com/"
	# fi

	cn=$(curl -fsSL -m 10 -s http://ipinfo.io/json | grep "\"country\": \"CN\"")
	HTTP_PREFIX="https://"
	LOCAL_ADDR=common
	if [ ! -z "$cn" ]; then
		LOCAL_ADDR=cn
		HTTP_PREFIX="https://ghproxy.com/"
	fi

	echo "local:${LOCAL_ADDR}"

	if [ $OSNAME != "macos" ]; then
		mkdir -p /www/server
		mkdir -p /www/wwwroot
		mkdir -p /www/wwwlogs
		mkdir -p /www/backup/database
		mkdir -p /www/backup/site

		if [ ! -d /www/server/mdserver-web ]; then
			_mdsw_sha256=$(echo $(sha256sum third_party/mdserver-web.tar.gz) | awk '{print $1}')
			if [ "415f6c84d76a868a57cefa9546c1126b45830156aa682357064cec780f4edae0" == "${_mdsw_sha256}" ]; then
				tar xf third_party/mdserver-web.tar.gz -C /www/server
			else
				echo "mdserver-web.tar.gz 校验不通过"
				exit 2
			fi
		fi

		# install acme.sh acme.sh 包已包含在 scripts/third_party/acme.sh 下
		_acme_sha256=$(echo $(sha256sum third_party/acme.sh.tar.gz) | awk '{print $1}')
		if [ "14a28e2dfd452ffb039ab05c7ced48997917c5525029719693229d840b99e53b" == "${_acme_sha256}" ]; then
			tar xf third_party/acme.sh.tar.gz -C third_party
			cd third_part/acme.sh && bash acme.sh install
		else
			echo "acm.sh.tar.gz 校验不通过"
			exit 2
		fi
	fi

	echo "use system version: ${OSNAME}"

	if [ "${OSNAME}" == "macos" ]; then
		curl --insecure -fsSL https://code.midoks.me/midoks/mdserver-web/raw/branch/master/scripts/install/macos.sh | bash
	else
		cd /www/server/mdserver-web && bash scripts/install/${OSNAME}.sh
	fi

	if [ "${OSNAME}" == "macos" ]; then
		echo "macos end"
		exit 0
	fi

	cd /www/server/mdserver-web && bash cli.sh start
	isStart=$(ps -ef | grep 'gunicorn -c setting.py app:app' | grep -v grep | awk '{print $2}')
	n=0
	while [ ! -f /etc/rc.d/init.d/mw ]; do
		echo -e ".\c"
		sleep 1
		let n+=1
		if [ $n -gt 20 ]; then
			echo -e "start mw fail"
			exit 1
		fi
	done

	cd /www/server/mdserver-web && bash /etc/rc.d/init.d/mw stop
	cd /www/server/mdserver-web && bash /etc/rc.d/init.d/mw start
	cd /www/server/mdserver-web && bash /etc/rc.d/init.d/mw default

	sleep 2
	if [ ! -e /usr/bin/mw ]; then
		if [ -f /etc/rc.d/init.d/mw ]; then
			ln -s /etc/rc.d/init.d/mw /usr/bin/mw
		fi
	fi

	endTime=$(date +%s)
	((outTime = (${endTime} - ${startTime}) / 60))
	echo -e "Time consumed:\033[32m $outTime \033[0mMinute!"

} 1> >(tee mw-install.log) 2>&1

echo -e "\nInstall completed. If error occurs, please contact us with the log file mw-install.log ."
echo "安装完毕，如果出现错误，请带上同目录下的安装日志 mw-install.log 联系我们反馈."
