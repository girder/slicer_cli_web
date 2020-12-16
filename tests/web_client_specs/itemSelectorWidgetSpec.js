girderTest.importPlugin('jobs', 'worker', 'slicer_cli_web');

var slicer;
girderTest.promise.done(function () {
    slicer = girder.plugins.slicer_cli_web;
});

girderTest.startApp();


describe('browser hierarchy paginated selection', function () {
    var user, folder, subfolder, item, widget, itemlist;
    var testEl;
    var transition;

    beforeEach(function () {
        testEl = $('<div/>').appendTo('body');
        $('.modal').remove();

        transition = $.support.transition;
        $.support.transition = false;
    });
    afterEach(function () {
        testEl.remove();
        $('.modal').remove();
        $.support.transition = transition;
    });
    it('register a user', function () {
        runs(function () {
            var _user = new girder.models.UserModel({
                login: 'mylogin2',
                password: 'mypassword',
                email: 'email2@girder.test',
                firstName: 'First',
                lastName: 'Last'
            }).on('g:saved', function () {
                user = _user;
            });

            _user.save();
        });

        waitsFor(function () {
            return !!user;
        }, 'user registration');
    });

    it('create top level folder', function () {
        runs(function () {
            var _folder = new girder.models.FolderModel({
                parentType: 'user',
                parentId: user.get('_id'),
                name: 'top level folder'
            }).on('g:saved', function () {
                folder = _folder;
            });

            _folder.save();
        });

        waitsFor(function () {
            return !!folder;
        }, 'folder creation');
    });

    it('create subfolder', function () {
        runs(function () {
            var _subfolder = new girder.models.FolderModel({
                parentType: 'folder',
                parentId: folder.get('_id'),
                name: 'subfolder'
            }).on('g:saved', function () {
                subfolder = _subfolder;
            });

            _subfolder.save();
        });

        waitsFor(function () {
            return !!subfolder;
        }, 'subfolder creation');
    });

    it('create item', function () {
        runs(function () {
            var _item = new girder.models.ItemModel({
                folderId: folder.get('_id'),
                name: 'an item'
            }).on('g:saved', function () {
                item = _item;
            });

            _item.save();
        });

        waitsFor(function () {
            return !!item;
        }, 'item creation');
    });

    it('create lots of items', function () {
        runs(function () {
            itemlist = [];
            for (var i = 0; i < 20; i++) {
                var _item = new girder.models.ItemModel({
                    folderId: folder.get('_id'),
                    name: ('item#: ' + i)
                }).on('g:saved', function () {
                    itemlist.push(_item);
                });

                _item.save();
            }
        });
        waitsFor(function () {
            return itemlist.length === 20;
        }, 'item creation');
    });

    it('test the itemListWidget for new functionality', function () {
        runs(function () {
            $('.g-hierarchy-widget-container').remove();
            testEl.remove();
            widget = new slicer.views.ItemSelectorWidget({
                parentView: null,
                el: testEl,
                helpText: 'This is helpful',
                titleText: 'This is a title',
                rootPath: folder,
                defaultSelectedResource: item,
                selectItem: true,
                showItems: true,
                model: new slicer.models.WidgetModel({
                    type: 'multi',
                    title: 'Title',
                    id: 'item-widget'
                })

            }).render();
        });

        waitsFor(function () {
            return $(widget.$el).is(':visible');
        }, 'waiting for visibility of the widget');


        waitsFor(function () {
            return $('.g-hierarchy-widget').length > 0;
        }, 'the hierarchy widget to display');

        runs(function () {
            waits(3000);
            console.log('_SCREENSHOT__Initial');
        })

        runs(function () {
            $('#g-input-element').val('[0-9][1-3]');
            $('#g-input-element').trigger('input');
        }, 'set regEx to [0-9][1-3]');

        waitsFor(function () {
            return $('.g-selected .g-item-list-link').length > 0;
        });
        runs(function () {
            var name_list = [];
            $('.g-selected .g-item-list-link').each( function(index, item) {
                name_list.push($(this)
                .clone()
                .children()
                .remove()
                .end()
                .text());
            });
            expect(name_list.includes("item#: 10")).toBe(false);
            expect(name_list.includes("item#: 11")).toBe(true);
            expect(name_list.includes("item#: 12")).toBe(true);
            expect(name_list.includes("item#: 13")).toBe(true);
            expect(name_list.includes("item#: 14")).toBe(false);
        }, 'testing for [0-9][1-3] regEx');

        runs(function () {
            $('#g-input-element').val(' [4-7]$');
            $('#g-input-element').trigger('input');
        }, 'set regEx to [0-9][1-3]');
        waitsFor(function () {
            return $('.g-selected .g-item-list-link').length > 0;
        });
        runs(function () {
            var name_list = [];
            $('.g-selected .g-item-list-link').each( function(index, item) {
                name_list.push($(this)
                .clone()
                .children()
                .remove()
                .end()
                .text());
            });
            expect(name_list.includes("item#: 4")).toBe(true);
            expect(name_list.includes("item#: 5")).toBe(true);
            expect(name_list.includes("item#: 6")).toBe(true);
            expect(name_list.includes("item#: 7")).toBe(true);
            expect(name_list.includes("item#: 14")).toBe(false);
            expect(name_list.includes("item#: 17")).toBe(false);
        }, 'Testing for End / [4-7]$/ regex');

        runs(function () {
            $('#g-input-element').val('');
            $('#g-input-element').trigger('input');
        }, 'set regEx to empty');

        waitsFor(function () {
            return $('.g-selected .g-item-list-link').length > 0;
        });
        runs(function () {
            expect($('.g-selected .g-item-list-link').length).toBe(21)
        }, 'Testing empty Regex value');
        
        runs(function () {
            $('#g-input-element').val('\\');
            $('#g-input-element').trigger('input');
        }, 'set regEx to error');

        waitsFor(function () {
            return $('.g-selected .g-item-list-link').length == 0;
        });
        runs(function () {
            expect($('.g-validation-failed-message:visible').length).toBe(1)
        }, 'Testing empty Error Regex value');

        runs(function () {
            $('g-submit-button').click();
            expect($('.g-validation-failed-message:visible').length).toBe(1)
        }, 'Attempting to Submit an invalid Regex');

        runs(function () {
            waits(3000);
            console.log('__SCREENSHOT__TEST');
        })

    })

    xit('test browserwidget defaultSelectedResource [item with paginated views]', function () {
        runs(function () {
            $('.g-hierarchy-widget-container').remove();
            testEl.remove();
            widget = new girder.views.widgets.BrowserWidget({
                parentView: null,
                el: testEl,
                helpText: 'This is helpful',
                titleText: 'This is a title',
                defaultSelectedResource: item,
                selectItem: true,
                paginated: true,
                highlightItem: true,
                showItems: true
            }).render();
        });

        waitsFor(function () {
            return $(widget.$el).is(':visible');
        });

        waitsFor(function () {
            return $('.g-hierarchy-widget').length > 0 &&
                               $('.g-item-list-link').length > 0;
        }, 'the hierarchy widget to display');

        runs(function () {
            expect(widget.$('#g-selected-model').val()).toBe('an item');
            expect($('.g-hierarachy-paginated-bar').length).toBe(1);
            expect($('.g-hierarachy-paginated-bar').hasClass('g-hierarchy-sticky')).toBe(true);
            expect($('.g-hierarchy-breadcrumb-bar').hasClass('g-hierarchy-sticky')).toBe(true);
        }, 'Make sure paginated text is displayed with proper settings');
    });
});
