// validate based on jquery validate

function isNullOrEmpty(value) {
    return value==null || value=="";
}

function checkEmail(value){
    var reg = /^([\.0-9A-Za-z_-]){1,59}@([0-9a-z])+(\.[a-z]{2,3})+/;
    return reg.test(value);
}

function checkName(value) {
    //var reg = /^([\.0-9-A-Za-z_\u4E00-\u9FA5]){1,64}/;
    var reg = /^[a-zA-Z0-9][a-zA-Z0-9_\-\.]{0,128}$/;
    return reg.test(value);
}

jQuery.validator.addMethod("positiveinteger", function(value, element) {
    var pattern = /^[1-9]\d*$/;
    return (this.optional(element) && isNullOrEmpty(value)) || pattern.test(value);
}, "请输入正整数");

jQuery.validator.addMethod("nonnegativeinteger", function (value, element) {
    var pattern = /^(0|[1-9]\d*)$/;
    return (this.optional(element) && isNullOrEmpty(value)) || pattern.test(value);
}, "请输入非负整数");

jQuery.validator.addMethod("isEmail", function(value, element) {
    return this.optional(element) || checkEmail(value);
}, "邮箱格式不正确");

jQuery.validator.addMethod("isInteger", function(value, element) {
    var pattern = /^[1-9]\d*$/;
    return this.optional(element) || pattern.test(value);
}, "内容只能为正整数");

jQuery.validator.addMethod("checkip", function(value, element) {  
  var ip = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;  
  return this.optional(element) || (ip.test(value) && (RegExp.$1 < 256 && RegExp.$2 < 256 && RegExp.$3 < 256 && RegExp.$4 < 256));
}, "Ip地址格式错误"); 

jQuery.validator.addMethod("ipusable", function(value, element) {  
  var ip = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-4]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[1-9])$/;  
  return this.optional(element) || (ip.test(value) && (RegExp.$1 < 256 && RegExp.$2 < 256 && RegExp.$3 < 256 && RegExp.$4 < 256));
}, "该IP地址不可用");

jQuery.validator.addMethod("cidr", function(value, element) {
    if (this.optional(element))
        return true;
    var ip = null, mask = null;
    var ip_mask = value.split('/');
    ip = ip_mask[0];
    if (ip_mask.length > 2)
        return false;
    else if (ip_mask.length == 2) {
        if (!ip_mask[1])
            return false; // '0.0.0.0/ not allowed'
        else
            var temp = parseInt(ip_mask[1], 10);
            if (temp != ip_mask[1])
                return false;
            mask = temp;
    }
    
    var checkers = {
        'IPv4': {
            'regex': /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/,
            'mask_min': 0,
            'mask_max': 32
        },
        'IPv6': {
            // FIXME: i am not sure whether this ipv6 regex works well.
            'regex': /^((([0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4})|(([0-9A-Fa-f]{1,4}:){6}:[0-9A-Fa-f]{1,4})|(([0-9A-Fa-f]{1,4}:){5}:([0-9A-Fa-f]{1,4}:)?[0-9A-Fa-f]{1,4})|(([0-9A-Fa-f]{1,4}:){4}:([0-9A-Fa-f]{1,4}:){0,2}[0-9A-Fa-f]{1,4})|(([0-9A-Fa-f]{1,4}:){3}:([0-9A-Fa-f]{1,4}:){0,3}[0-9A-Fa-f]{1,4})|(([0-9A-Fa-f]{1,4}:){2}:([0-9A-Fa-f]{1,4}:){0,4}[0-9A-Fa-f]{1,4})|(([0-9A-Fa-f]{1,4}:){6}((b((25[0-5])|(1d{2})|(2[0-4]d)|(d{1,2}))b).){3}(b((25[0-5])|(1d{2})|(2[0-4]d)|(d{1,2}))b))|(([0-9A-Fa-f]{1,4}:){0,5}:((b((25[0-5])|(1d{2})|(2[0-4]d)|(d{1,2}))b).){3}(b((25[0-5])|(1d{2})|(2[0-4]d)|(d{1,2}))b))|(::([0-9A-Fa-f]{1,4}:){0,5}((b((25[0-5])|(1d{2})|(2[0-4]d)|(d{1,2}))b).){3}(b((25[0-5])|(1d{2})|(2[0-4]d)|(d{1,2}))b))|([0-9A-Fa-f]{1,4}::([0-9A-Fa-f]{1,4}:){0,5}[0-9A-Fa-f]{1,4})|(::([0-9A-Fa-f]{1,4}:){0,6}[0-9A-Fa-f]{1,4})|(([0-9A-Fa-f]{1,4}:){1,7}:))$/,
            'mask_min': 0,
            'mask_max': 128
        }
    };
    
    var valid = false;
    for (var ip_version in checkers) {
        var checker = checkers[ip_version];
        
        if (checker.regex.test(ip)) {
            if (!mask || (mask && mask >= checker.mask_min && mask <= checker.mask_max)) {
                valid = true;
            }
            break;
        }
    }
    return valid;
}, "CIDR格式错误");

jQuery.validator.addMethod("notLessThan", function (value, element, params) {
    // FIXME: params is the target's id, we can use name instead.
    var target_value = $(params).val(); 
    if (!target_value)
        return true;
    var compare_value = parseInt(target_value, 10);
    var self_value = parseInt(value, 10);
    
    if (self_value >= compare_value)
        return true;
    else
        return false;
}, "不小于");

jQuery.validator.addMethod("integer", function (value, element) {
    return parseInt(value, 10) == value;
}, "请输入整数"); // both positive and negative integer

jQuery.validator.addMethod("size", function(value, element) {
    return this.optional(element) || checkQuota(value);
}, "配额不能为0");

jQuery.validator.addMethod("isname", function (value, element) {
    return this.optional(element) || checkName(value);
}, "名称格式不正确");

// jQuery.validator.addMethod(
//     "selectNone",
//     function (value, element) {
//         if(value == "请选择"){
//             alert('false');
//             return false;
//         }else {
//             alert('true');
//             return true;
//         }
//     },
//     "必须选一项"
// );


function checkQuota(value){
  var FirstChar=value.substr(0,1);
  if(FirstChar=="0"){
    return false;
  }
  return true;
}