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
}, "端口号只能为正整数");

jQuery.validator.addMethod("checkip", function(value, element) {  
  var ip = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;  
  return this.optional(element) || (ip.test(value) && (RegExp.$1 < 256 && RegExp.$2 < 256 && RegExp.$3 < 256 && RegExp.$4 < 256));
}, "Ip地址格式错误"); 

jQuery.validator.addMethod("ipusable", function(value, element) {  
  var ip = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-4]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[1-9])$/;  
  return this.optional(element) || (ip.test(value) && (RegExp.$1 < 256 && RegExp.$2 < 256 && RegExp.$3 < 256 && RegExp.$4 < 256));
}, "该IP地址不可用");

jQuery.validator.addMethod("size", function(value, element) {
    return this.optional(element) || checkQuota(value);
}, "配额不能为0");

jQuery.validator.addMethod("isname", function (value, element) {
    return this.optional(element) || checkName(value);
}, "名称格式不正确");

jQuery.validator.addMethod("phonenumber",function(value,element){
        var reg = /^[0-9]{8,11}$/;
        return this.optional(element)||  reg.test(value);
    },"只能填写11位电话号码");

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