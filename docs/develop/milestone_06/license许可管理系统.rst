license许可管理系统
=====================

用户管理
---------------------
    管理员可创建用户，编辑，删除用户


实例管理
---------------------
    主要用于管理员分配实例及其配额，然后由用户提交其主机信息，生成license文件后供用户下载使用
   
   
实例状态
---------------------  
    TOUPLOAD: "未上传主机信息",
    INFOERROR: "主机信息被篡改",
    TODOWNLOAD: "可下载最新 License",
    DOWNLOADERROR: "下载异常",
    EXPIRED: "实例已过期"
    

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
    mac地址
    sn号
    
2. 模型设计
    class Permission:
        USER = 0x02
        ADMINISTER = 0x80
        
    class InstanceStatus(object):
        TOUPLOAD = 'TOUPLOAD'
        INFOERROR = 'INFOERROR'
        TODOWNLOAD = 'TODOWNLOAD'
        DOWNLOADERROR = 'DOWNLOADERROR'
        EXPIRED = 'EXPIRED'

    class Role(db.Model):
        __tablename__ = 'roles'
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(64), unique=True)
        description = db.Column(db.Text)
        permissions = db.Column(db.Integer)
        users = db.relationship('User', backref='role', lazy='dynamic')
    
    class User(UserMixin,TimestampMixin, db.Model):
        __tablename__ = 'users'
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(64), unique=True, index=True)
        email = db.Column(db.String(64), unique=True, index=True)
        phone = db.Column(db.String(11))
        organization = db.Column(db.String(64), index=True)
        os_auth_url = db.Column(db.String(64))
        is_active = db.Column(db.Boolean, default=True)
        role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
        origin_password = db.Column(db.String(128))
        password_hash = db.Column(db.String(128), default="")
        confirmed = db.Column(db.Boolean, default=False)
        
    class Instance(db.Model, IdMixin, TimestampMixin):
        instancename = db.Column(db.String(64), unique=True, index=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
        max_vm = db.Column(db.Integer, default=0)
        max_image = db.Column(db.Integer, default=0)
        max_user = db.Column(db.Integer, default=0)
        max_vcpu = db.Column(db.Integer, default=0)
        max_vmem = db.Column(db.Integer, default=0)
        max_vdisk = db.Column(db.Integer, default=0)
        status = db.Column(db.String(64), default='TOUPLOAD')
        expired_time = db.Column(db.DateTime, default=datetime.datetime.now)
        mac = db.Column(db.String(256), default='')
        serial_number = db.Column(db.String(256), default='')
        check_code = db.Column(db.Text(), default='')
        public_key = db.Column(db.Text(), default='')
        download = db.Column(db.Integer, default=0)

        

相关接口
---------------------


URL列表::
    /users  用于显示用户列表
    /create_user    用于创建用户
    /update_user_status 用于控制用户账户的激活状态
    /update_user    用于更新用户信息
    /delete_users   用于删除用户
    /instances  用于显示实例列表
    /add_instance     用于添加实例
    /update_instance     用于更新实例
    /delete_instances   用于删除实例
    /upload_hostinfo  用于上传实例的主机信息
    /download_license 用于生成许可文件，许可文件的下载使用另外一个url进行，/static/license/<<Instancename>>_LICENSE
