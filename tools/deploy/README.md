# 云晫云课室 1.7.1 版

云晫云课室 1.7.1 版

## 版本信息

版本号： web_edu_v1.7.1-20161201

分支： master

gitlab版本： ec1e75074643160a8ffe9ffca9a2303a625ad135


## 部署

### 前置要求
```
操作系统: Ubuntu Server 14.04.5 LTS
```

### 安装步骤

* 步骤 1:
根据实际情况配置 localrc 文件内的环境变量值，例如，根据实际情况设置 openstack 和 ganglia 的相关参数
    ```
    # openstack
    export OS_AUTH_URL=http://172.18.215.3:5000/v2.0
    ...
    # ganglia
    export GANGLIA_URL=http://172.18.215.3:8088/ganglia
    ```

* 步骤 2:
运行 run.sh 脚本，命令如下
    ```
    ./run.sh
    ```

* 步骤 3:
登陆网页
    ```
    http://ip/phoenix
    ```

## 更新说明

1. 修复了部分 bug

## 版本控制

略

## 许可证

略

## 鸣谢

无
