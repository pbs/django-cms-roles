django.jQuery(document).ready(function(){
    var $ = django.jQuery;
    var default_chosen_settings = {search_contains: true};

    $('.user_settings').formset({
        prefix: 'user-roles',
        addText: 'Assign another user to this site',
        deleteText: '',
        added: function(row){
            $('select', row).chosen(default_chosen_settings);
            $('.assign-pages', row).hide();
        },
    });

    function init_page_formset(user_settings){
        var user_role_pair = get_user_and_role(user_settings);
        var prefix = 'user-' + user_role_pair.user.val();
        $('.page_form', user_settings).formset({
            prefix: prefix,
            addText: 'Assign another page',
            formCssClass: 'page_form',
            added: function(row){
                $('select', row).chosen(default_chosen_settings);
            },
        });
    }

    $('.user_settings').each(function(){
        var user_settings = $(this);
        init_page_formset(user_settings);
    });


    $('#site_selector').change(function(){
        var site_pk = $(this).val();
        window.location = '/admin/cmsroles/usersetup/?site=' + site_pk;
    });

    function submit_userformset(next_action){
        $('#next_on_save').attr('value', next_action);
        $('#user_formset').submit();
    }

    $('#save').click(function(){
        submit_userformset('save');
    });

    $('#save_and_continue').click(function(){
        submit_userformset('continue');
    });

    $('select').chosen(default_chosen_settings);

    function get_user_and_role(user_settings_div){
        return {
            user: $('select[name$="user"]', user_settings_div),
            role: $('select[name$="role"]', user_settings_div)
        }
    }

    $('#search_box').bind('keyup input', function(){
        var search_word = $(this).val();
        search_word = search_word.toLowerCase();
        $.each( $('.user_settings'), function(i, val){
            var self = $(this);
            var user = $('span', self).first().html();
            user = user.toLowerCase();
            if (user.indexOf(search_word) === -1){
                self.hide();
            } else {
                self.show();
            }
        });
    });

    $('.assign-pages').each(function(){
        var user_settings = $(this).parent('.user_settings');
        var role = $('select[name$="role"]', user_settings).val();
        if (document.roles[role] || role === ""){
            $(this).hide();
        }
    })

    function toggleEnableFormSubmit(enable){
        if(enable){
            $('#save_and_continue, #save').removeAttr('disabled');
        } else {
            $('#save_and_continue, #save').attr('disabled', 'disabled');
        }
    }

    function fetch_pages(user_settings, hooks){
        var user_role_pair = get_user_and_role(user_settings);
        if (!user_role_pair.user.val() || !user_role_pair.role.val()){
            hooks.error_hook(false);
            return;
        }
        var current_site = $('#site_selector').find(":selected").val()
        toggleEnableFormSubmit(false);
        $.ajax({
            type: 'GET',
            url: '/admin/cmsroles/get_page_formset/',
            data: {
                'user': user_role_pair.user.val(),
                'role': user_role_pair.role.val(),
                'site': current_site
            },
            success: function(data, textStatus){
                if (data.success){
                    hooks.success_hook();
                    user_settings.append(data.page_formset);
                    init_page_formset(user_settings);
                    $('.page_form select', user_settings).chosen(
                        default_chosen_settings);
                } else {
                    //Even tough the ajax call was a sucess (200 status code),
                    //a known error might have happend
                    alert(data.error_msg);
                    hooks.error_hook(false);
                }
            },
            error: function(data, textStatus){
                hooks.error_hook(true);
            },
            complete: function(data, textStatus){
                toggleEnableFormSubmit(true);
            }
        });
    }

    $('.assign-pages').click(function(e){
        e.preventDefault();
        var assign_pages_link = $(this);
        var user_settings = $(this).parent('.user_settings');
        var waiting_pages = $('.waiting-pages', user_settings);
        waiting_pages.css('visibility', 'visible');
        fetch_pages(user_settings, {
            success_hook: function(){
                assign_pages_link.hide();
                waiting_pages.css('visibility', 'hidden');
            },
            error_hook: function(is_unexpected){
                assign_pages_link.show();
                waiting_pages.css('visibility', 'hidden');
                if (is_unexpected){
                    alert('Unexpected error!');
                }
            }
        });
    });

    function remove_page_formset(user_settings){
        var page_formset = $('.page_formset', user_settings);
        if (page_formset.length > 0){
            page_formset.remove();
        }
    }

    $('.user_settings select[name$="role"]').change(function(e){
        var selected_role = $(this).val();
        var is_site_wide = document.roles[selected_role];
        var user_settings = $(this).parents('.user_settings');
        var user_role_pair = get_user_and_role(user_settings);
        if  (user_role_pair.user.val() === ""){
            return
        }

        if (user_role_pair.role.val() === "" || is_site_wide){
            remove_page_formset(user_settings);
            $('.assign-pages', user_settings).hide();
        }else{
            var waiting_icon = $('.waiting-change', user_settings);
            waiting_icon.css('visibility', 'visible');
            fetch_pages(user_settings, {
                success_hook: function(){
                    waiting_icon.css('visibility', 'hidden');
                },
                error_hook: function(is_unexpected){
                    $('.assign-pages', user_settings).show();
                    waiting_icon.css('visibility', 'hidden');
                    if (is_unexpected){
                        alert('Unexpected error');
                    }
                }
            });
        }
    });

    $('.user_settings select[name$="user"]').change(function(e){
        var user_settings = $(this).parents('.user_settings');
        var user_role_pair = get_user_and_role(user_settings);
        var role = user_role_pair.role.val();
        var is_site_wide = document.roles[role];
        if (!is_site_wide && role !== ""){
            remove_page_formset(user_settings);
            var assign_pages_link = $('.assign-pages', user_settings);
            var waiting_icon = $('.waiting-change', user_settings);
            waiting_icon.css('visibility', 'visible');
            fetch_pages(user_settings, {
                success_hook: function(){
                    assign_pages_link.hide();
                    waiting_icon.css('visibility', 'hidden');
                },
                error_hook: function(is_unexpected){
                    waiting_icon.css('visibility', 'hidden');
                    if (is_unexpected){
                        alert('Unexpected error');
                    }
                }
            });
        }
    });

});
