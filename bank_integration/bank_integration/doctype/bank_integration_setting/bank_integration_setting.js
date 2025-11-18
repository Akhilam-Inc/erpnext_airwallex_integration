// Copyright (c) 2025, Akhilam Inc and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Integration Setting', {
    refresh: function (frm) {
        // Add sync button if conditions are met
        if (frm.doc.sync_old_transactions &&
            frm.doc.sync_status !== 'In Progress' &&
            frm.doc.sync_status !== 'Completed with Errors' &&
            frm.doc.from_date &&  // Changed from frm.doc.from
            frm.doc.to_date && frm.doc.enable_airwallex == 1) {    // Changed from frm.doc.to

            frm.add_custom_button(__('Sync Old Transactions'), function () {
                frappe.confirm(
                    'Are you sure you want to start syncing transactions from ' +
                    frappe.datetime.str_to_user(frm.doc.from_date) + ' to ' +  // Changed
                    frappe.datetime.str_to_user(frm.doc.to_date) + '?',        // Changed
                    function () {
                        frappe.call({
                            method: 'start_transaction_sync',
                            doc: frm.doc,
                            callback: function (r) {
                                if (!r.exc) {
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __('Actions'));
        }

        // Add restart sync button for failed or completed syncs
        if (frm.doc.sync_old_transactions &&
            (frm.doc.sync_status === 'Failed' ||
                frm.doc.sync_status === 'Completed with Errors') &&
            frm.doc.from_date &&  // Changed
            frm.doc.to_date && frm.doc.enable_airwallex == 1) {    // Changed

            frm.add_custom_button(__('Restart Transaction Sync'), function () {
                frappe.confirm(
                    'This will restart the transaction sync from ' +
                    frappe.datetime.str_to_user(frm.doc.from_date) + ' to ' +  // Changed
                    frappe.datetime.str_to_user(frm.doc.to_date) + '. ' +      // Changed
                    'Are you sure you want to proceed?',
                    function () {
                        frappe.call({
                            method: 'restart_transaction_sync',
                            doc: frm.doc,
                            callback: function (r) {
                                if (!r.exc) {
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __('Actions'));
        }

        // Add stop sync button for in-progress syncs
        if (frm.doc.sync_status === 'In Progress' && frm.doc.enable_airwallex == 1) {
            frm.add_custom_button(__('Stop Transaction Sync'), function () {
                frappe.confirm(
                    'Are you sure you want to stop the current transaction sync?',
                    function () {
                        frappe.call({
                            method: 'stop_transaction_sync',
                            doc: frm.doc,
                            callback: function (r) {
                                if (!r.exc) {
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __('Actions'));
        }

        // Listen for real-time updates
        frappe.realtime.on('transaction_sync_progress', function (data) {
            if (data.total > 0) {
                frm.set_value('sync_progress', data.progress);
                frm.set_value('processed_records', data.processed);
                frm.set_value('total_records', data.total);
                frm.set_value('sync_status', data.status);
                frm.refresh_fields();
                frm.refresh(); // Refresh to update button visibility
            }
        });

        frappe.realtime.on('transaction_sync_complete', function (data) {
            frappe.show_alert({
                message: data.message,
                indicator: data.status === 'success' ? 'green' : 'red'
            });
            frm.reload_doc();
        });

        // Skript buttons
        if (frm.doc.enable_skript) {
            // Test Authentication
            frm.add_custom_button(__('Test Authentication'), function () {
                frm.call('test_skript_authentication').then(r => {
                    if (r.message) {
                        frappe.show_alert({
                            message: __('Skript authentication successful'),
                            indicator: 'green'
                        });
                    }
                });
            }, __('Skript'));

            // Fetch Accounts
            frm.add_custom_button(__('Fetch Accounts'), function () {
                frappe.confirm(
                    'This will fetch accounts from Skript API and populate the Skript Accounts table. Continue?',
                    function () {
                        frappe.show_alert({
                            message: __('Fetching accounts...'),
                            indicator: 'blue'
                        });

                        frm.call('fetch_and_create_skript_accounts').then(r => {
                            if (r.message) {
                                // Reload the entire document to show saved child records
                                frappe.show_alert({
                                    message: __('Accounts fetched successfully. Reloading...'),
                                    indicator: 'green'
                                });

                                setTimeout(() => {
                                    frm.reload_doc();
                                }, 1000);
                            }
                        });
                    }
                );
            }, __('Skript'));

            // Validate Mapping
            frm.add_custom_button(__('Validate Mapping'), function () {
                frm.call('validate_skript_account_mapping').then(r => {
                    if (r.message) {
                        // Has unmapped accounts
                        let account_list = r.message.map(acc =>
                            `• ${acc.display_name} (${acc.masked_number || acc.account_id})`
                        ).join('<br>');

                        frappe.msgprint({
                            title: __('Unmapped Accounts'),
                            indicator: 'red',
                            message: `<b>The following accounts are not mapped:</b><br><br>${account_list}<br><br>Please map them to ERPNext Bank Accounts.`
                        });
                    } else {
                        // All mapped
                        frappe.msgprint({
                            title: __('All Mapped'),
                            indicator: 'green',
                            message: '✅ All Skript accounts are mapped to ERPNext Bank Accounts!'
                        });
                    }
                });
            }, __('Skript'));

            // Start Sync
            frm.add_custom_button(__('Start Sync'), function () {
                if (!frm.doc.from_date || !frm.doc.to_date) {
                    frappe.msgprint(__('Please set From and To dates'));
                    return;
                }
                frm.call('validate_skript_account_mapping').then(r => {
                    if (r.message) {
                        // Has unmapped accounts
                        let account_list = r.message.map(acc =>
                            `• ${acc.display_name} (${acc.masked_number || acc.account_id})`
                        ).join('<br>');

                        frappe.msgprint({
                            title: __('Unmapped Accounts'),
                            indicator: 'red',
                            message: `<b>The following accounts are not mapped:</b><br><br>${account_list}<br><br>Please map them to ERPNext Bank Accounts.`
                        });
                    } else {
                        if (!frm.doc.skript_from_date || !frm.doc.skript_to_date) {
                            frappe.msgprint(__('Please set Skript From and To dates'));
                            return;
                        }
                           // Will validate mapping and show error if unmapped accounts exist
                            frm.call('start_skript_transaction_sync');
                    }
                });
             
            }, __('Skript'));
        }

        // Restart Sync (only show if sync failed or stopped)
        if (frm.doc.skript_sync_status && 
            ['Failed', 'Stopped', 'Completed with Errors'].includes(frm.doc.skript_sync_status)) {
            frm.add_custom_button(__('Restart Sync'), function() {
                frm.call('restart_skript_transaction_sync');
            }, __('Skript'));
        }

        // Stop Sync (only show if in progress)
        if (frm.doc.skript_sync_status === 'In Progress') {
            frm.add_custom_button(__('Stop Sync'), function() {
                frappe.confirm(
                    'Are you sure you want to stop the current sync?',
                    function() {
                        frm.call('stop_skript_transaction_sync');
                    }
                );
            }, __('Skript'));
        }

    },
    enable_airwallex: function (frm) {
        // Refresh to show/hide button when checkbox changes
        frm.refresh();
    },
    sync_old_transactions: function (frm) {
        // Refresh to show/hide button when checkbox changes
        frm.refresh();
    },

    sync_status: function (frm) {
        // Refresh to show/hide button when status changes
        frm.refresh();
    }
});
