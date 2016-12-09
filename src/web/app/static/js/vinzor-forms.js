/*
    Use To Simplify Form Design
    2016/8/1 ChengKang : Init
*/

/*
    Sometimes we expect that one select field's change event trigger another
    form field to show or hide, here is the solution.
*/
$(document).on("change", 'select.switchable', function (evt) {
    var $fieldset = $(evt.target).closest('form'),
    $switchables = $fieldset.find('.switchable');

    $switchables.each(function (index, switchable) {
        var $switchable = $(switchable),
        slug = $switchable.data('slug');
        if ($switchable.is('.select2'))
            // TODO: if the element is a select2, it always be hidden, we should judge whether its parent is visible.
            // Maybe, we can use the parent's visibility as the element's visibility
            visible = $switchable.prev().is(':visible');
        else
            visible = $switchable.is(':visible');
        val = $switchable.val();

        $fieldset.find('.switched[data-switch-on*="' + slug + '"]').each(function(index, input){
            var $input = $(input),
            data = $input.data(slug + "-" + val);
            if (typeof data === "undefined" || !visible) {
                $input.closest('.form-group').hide();
            } else {
                //$('label[for=' + $input.attr('id') + ']').html(data); // if here use name, it will take effect
                $input.closest('.form-group').show();
            }
        });
    });
});

$('select.switchable').trigger('change');
  