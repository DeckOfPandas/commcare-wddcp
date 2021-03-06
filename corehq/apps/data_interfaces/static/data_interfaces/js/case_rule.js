hqDefine("data_interfaces/js/case_rule.js", function() {

    $(function() {
        if(hqImport("hqwebapp/js/initial_page_data.js").get('read_only_mode')) {
            $('#rule-definition :input').prop('disabled', true);
        }

        $("#rule-definition-form").submit(function(event) {
            var result = true;
            var criteria_model = hqImport('data_interfaces/js/case_rule_criteria.js').get_criteria_model();

            if(criteria_model.selected_case_filter_id() !== 'select-one') {
                criteria_model.show_add_filter_warning(true);
                result = false;
            } else {
                criteria_model.show_add_filter_warning(false);
            }

            var actions_model = hqImport('data_interfaces/js/case_rule_actions.js').get_actions_model();
            if(actions_model.selected_case_action_id() !== 'select-one') {
                actions_model.show_add_action_warning(true);
                result = false;
            } else {
                actions_model.show_add_action_warning(false);
            }

            return result;
        });
    });

});
