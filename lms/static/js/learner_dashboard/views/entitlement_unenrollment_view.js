(function(define) {
    'use strict';
    define(['backbone',
        'jquery',
        'gettext',
        'edx-ui-toolkit/js/utils/html-utils'
    ],
        function(Backbone, $, gettext, HtmlUtils) {
            return Backbone.View.extend({
                el: '.js-entitlement-unenrollment-modal',
                closeButtonSelector: '.js-entitlement-unenrollment-modal .js-entitlement-unenrollment-modal-close-btn',
                trackInfoSelector: '.js-entitlement-unenrollment-modal .js-entitlement-unenrollment-modal-track-info',
                refundInfoSelector: '.js-entitlement-unenrollment-modal .js-entitlement-unenrollment-modal-refund-info',
                errorInfoSelector: '.js-entitlement-unenrollment-modal .js-entitlement-unenrollment-modal-error-info',
                submitButtonSelector: '.js-entitlement-unenrollment-modal .js-entitlement-unenrollment-modal-submit',
                triggerSelector: '.js-entitlement-action-unenroll',
                mainPageSelector: '#dashboard-main',

                initialize: function(options) {
                    var view = this;
                    this.dashboardPath = options.dashboardPath;
                    this.signInPath = options.signInPath;

                    this.$submitButton = $(this.submitButtonSelector);
                    this.$trackInfo = $(this.trackInfoSelector);
                    this.$refundInfo = $(this.refundInfoSelector);
                    this.$errorInfo = $(this.errorInfoSelector);

                    this.$submitButton.on('click', this.handleSubmit.bind(this));

                    $(this.triggerSelector).each(function() {
                        var $trigger = $(this);

                        $trigger.on('click', view.handleTrigger.bind(view));

                        if (window.accessible_modal) {
                            window.accessible_modal(
                                '#' + $trigger.attr('id'),
                                view.closeButtonSelector,
                                '#' + view.$el.attr('id'),
                                view.mainPageSelector
                            );
                        }
                    });
                },

                handleTrigger: function(event) {
                    var $trigger = $(event.target),
                        courseName = $trigger.data('courseName'),
                        courseNumber = $trigger.data('courseNumber'),
                        isRefundable = $trigger.data('entitlementIsRefundable'),
                        apiEndpoint = $trigger.data('entitlementApiEndpoint');

                    // Convert to boolean.
                    isRefundable = isRefundable && isRefundable.toLowerCase() === 'true';

                    this.resetModal();
                    this.setTrackInfo(courseName, courseNumber);
                    this.setRefundInfo(isRefundable);
                    this.setSubmitData(apiEndpoint);

                    if (window.edx && window.edx.dashboard && window.edx.dashboard.dropdown) {
                        window.edx.dashboard.dropdown.toggleCourseActionsDropdownMenu(event);
                        this.$el.css('position', 'fixed');
                    }
                },

                handleSubmit: function() {
                    var apiEndpoint = this.$submitButton.data('entitlementApiEndpoint');

                    if (apiEndpoint === undefined) {
                        this.setError(gettext('Error: cannot process unenrollment request.'));
                        return;
                    }

                    $.ajax({
                        url: apiEndpoint,
                        method: 'DELETE',
                        complete: this.onComplete.bind(this)
                    });
                },

                resetModal: function() {
                    this.$submitButton.removeData();
                    this.$submitButton.prop('disabled', false);
                    this.$trackInfo.empty();
                    this.$refundInfo.empty();
                    this.$errorInfo.css('display', 'none');
                    this.$errorInfo.empty();
                },

                setError: function(message) {
                    this.$submitButton.prop('disabled', true);
                    this.$errorInfo.empty();
                    HtmlUtils.setHtml(
                        this.$errorInfo,
                        message
                    );
                    this.$errorInfo.css('display', 'block');
                },

                setTrackInfo: function(courseName, courseNumber) {
                    this.$trackInfo.empty();
                    HtmlUtils.setHtml(
                        this.$trackInfo,
                        HtmlUtils.interpolateHtml(
                            gettext('Are you sure you want to unenroll from {courseName} ({courseNumber})?'),
                            {
                                courseName: courseName,
                                courseNumber: courseNumber
                            }
                        )
                    );
                },

                setRefundInfo: function(isRefundable) {
                    var message = null;

                    if (isRefundable) {
                        message = gettext('You will be refunded the amount you paid.');
                    } else {
                        message = gettext('You will not be refunded the amount you paid.');
                    }

                    this.$refundInfo.empty();
                    HtmlUtils.setHtml(this.$refundInfo, message);
                },

                setSubmitData: function(apiEndpoint) {
                    this.$submitButton.removeData();
                    this.$submitButton.data('entitlementApiEndpoint', apiEndpoint);
                },

                onComplete: function(xhr) {
                    var status = xhr.status,
                        message = xhr.responseJSON && xhr.responseJSON.detail;

                    if (status === 204) {
                        window.location.href = this.dashboardPath;
                    } else if (status === 401 && message === 'Authentication credentials were not provided.') {
                        window.location.href = this.signInPath + '?next=' + encodeURIComponent(this.dashboardPath);
                    } else {
                        this.setError(gettext('Error: something went wrong while processing your request.'));
                    }
                }
            });
        }
    );
}).call(this, define || RequireJS.define);
