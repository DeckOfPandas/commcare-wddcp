/*global FormplayerFrontend */

FormplayerFrontend.module("SessionNavigate.Users", function(Users, FormplayerFrontend, Backbone, Marionette, $){
    Users.Views = {}
    Users.Views.RestoreAsBanner = Marionette.ItemView.extend({
        template: '#restore-as-banner-template',
        className: 'restore-as-banner-container',
        templateHelpers: function() {
            return {
                restoreAs: this.model.restoreAs,
            };
        },
    });
    Users.Views.UserRowView = Marionette.ItemView.extend({
        template: '#user-row-view-template',
        className: 'formplayer-request js-user',
        tagName: 'tr',
        events: {
            'click': 'onClickUser',
        },
        onClickUser: function(e) {
            Util.confirmationModal({
                title: gettext('Log in as ' + this.model.get('username') + '?'),
                message: _.template($('#user-data-template').html())(
                    { user: this.model.toJSON() }
                ),
                confirmText: gettext('Yes, log in as this user'),
                onConfirm: function() {
                    Users.Utils.logInAsUser(this.model.get('username'));
                    FormplayerFrontend.trigger('navigateHome');
                }.bind(this),
            });
        },
    });
    Users.Views.RestoreAsView = Marionette.CompositeView.extend({
        childView: Users.Views.UserRowView,
        childViewContainer: 'tbody',
        template: '#restore-as-view-template',
        limit: 10,
        initialize: function(options) {
            this.model = new Backbone.Model({
                page: options.page || 1,
                query: options.query || '',
            });
            this.model.on('change', function() {
                this.fetchUsers();
                this.navigate();
            }.bind(this));
            this.fetchUsers();
        },
        ui: {
            next: '.js-user-next',
            prev: '.js-user-previous',
            search: '.js-user-search',
            query: '.js-user-query',
            page: '.js-page',
        },
        events: {
            'click @ui.next': 'onClickNext',
            'click @ui.prev': 'onClickPrev',
            'click @ui.page': 'onClickPage',
            'submit @ui.search': 'onSubmitUserSearch',
        },
        templateHelpers: function() {
            return {
                total: this.collection.total,
                totalPages: this.totalPages(),
            };
        },
        navigate: function() {
            FormplayerFrontend.navigate(
                '/restore_as/' +
                this.model.get('page') + '/' +
                this.model.get('query')
            );
        },
        totalPages: function() {
            return Math.ceil(this.collection.total / this.limit);
        },
        fetchUsers: function() {
            this.collection.fetch({
                reset: true,
                data: JSON.stringify({
                    query: this.model.get('query'),
                    limit: this.limit,
                    page: this.model.get('page'),
                })
            }).done(this.render.bind(this));
        },
        onClickNext: function(e) {
            e.preventDefault();
            if (this.model.get('page') === this.totalPages()) {
                console.warn('Attempted to non existant page');
                return;
            }
            this.model.set('page', this.model.get('page') + 1);
        },
        onClickPrev: function(e) {
            e.preventDefault();
            if (this.model.get('page') === 1) {
                console.warn('Attempted to non existant page');
                return;
            }
            this.model.set('page', this.model.get('page') - 1);
        },
        onClickPage: function(e) {
            e.preventDefault();
            var page = $(e.currentTarget).data().page;
            this.model.set('page', page);
        },
        onSubmitUserSearch: function(e) {
            e.preventDefault();
            this.model.set({
                'query': this.ui.query.val(),
                'page': 1,  // Reset page to one when doing a query
            });
        },
    });
});

