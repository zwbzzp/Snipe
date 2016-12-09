license许可
=====================

许可信息显示
---------------------
1. 许可信息显示内容：管理系统序列号、许可服务器URL、许可到期时间、服务器MAC地址、服务器序列号、
                     最大并发桌面数量、最大镜像数量、最大并发用户数量、最大VCPU个数/桌面、
                     最大虚拟内存容量/桌面、最大虚拟磁盘容量/桌面

手动激活
---------------------
    主要由下载主机信息和上传许可文件两个功能按钮完成
1. 下载主机信息：由用户先填写管理系统的序列号、然后再点击该按钮生成主机信息，生成主机信息后，
                 管理系统会自动下载一个host_info_file文件。此时用户刷新页面可以看到管理系统
                 所处的服务器MAC地址及服务器序列号。用户可以使用host_info_file到license管理
                 系统上传信息，生成license文件。
2. 上传许可文件：在用户得到许可文件后可到管理系统中上传license文件进行激活。上传文件后管理系
                 统会先将文件保存到一个临时文件中，并进行解密读取，如果信息正确就将上传licen
                 se文件数据写入真正保存的license文件中。防止出现错误文件将旧license文件覆盖的
                 情况出现。如果上传的文件正确，则管理系统完成激活

自动激活
---------------------
    该功能主要由管理系统自动地完成，主要是结合手动激活的步骤进行的。
    
    

关键数据模型
---------------------
1. license文件解密后的内容格式（每项内容占一行）：
    最大并发桌面数量
    最大镜像数量
    最大并发用户数量
    最大VCPU个数
    最大虚拟内存容量
    最大虚拟磁盘容量
    许可到期时间
    
2. 管理系统的数据库设计（该模型主要用于保存许可的相关信息用于页面的读取，以及序列号的保存）
    class License(db.Model, IdMixin, TimestampMixin):
        __tablename__ = 'licenses'
        system_serial_number = db.Column(db.String(64), default="")
        server_url = db.Column(db.String(64), default="")
        expired_time = db.Column(db.DateTime, default=datetime.datetime.now())
        mac_address = db.Column(db.String(64), default="")
        server_serial_number = db.Column(db.String(64), default="")
        max_desktops = db.Column(db.Integer, default=0)
        max_images = db.Column(db.Integer, default=0)
        max_user = db.Column(db.Integer, default=0)
        max_vcpu = db.Column(db.Integer, default=0)
        max_vmem = db.Column(db.Integer, default=0)
        max_vdisk = db.Column(db.Integer, default=0)

相关接口
---------------------


URL列表::
    /about  用于显示license信息
    /host_info_file     用于下载管理系统主机信息
    /upload_license_file     用于上传许可信息
    /batch_update_license   用于更新管理系统序列号、许可服务器URL等信息
    /invoke_system  用于自动激活操作


LicenseUtils类主要接口::
    get_mac_address 获取主机mac地址
    get_serial_number   获取服务器序列号
    generate_host_info  生成主机信息
    get_license_info    从许可文件中提取信息
    get_license_info_from_upload_file   从上传的文件中提取许可信息
    check_max_desktops  检查当前并发桌面数量是否超过许可数量，如果是返回True，否则返回False
    check_max_images    检查当前镜像数量是否超过许可数量，如果是返回True，否则返回False
    check_max_users     检查当前并发用户数量是否超过许可数量，如果是返回True，否则返回False
    check_max_vcpu      检查总虚拟处理器数量是否超过许可数量，如果是返回True，否则返回False
    check_max_vmem      检查总虚拟内存容量是否超过许可容量，如果是返回True，否则返回False
    check_max_vdisk     检查总虚拟磁盘容量是否超过许可容量，如果是返回True，否则返回False
    check_expired_time  检查当前时间是否超过许可时间，如果是返回True，否则返回False
    download_license_file   自动从许可服务器下载许可文件，并激活。用于自动激活
    upload_hostinfo     自动上传主机信息到许可服务器。用于自动激活