import Vuex from 'vuex';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import HistoryDetailed from '../../src/components/history-detailed.vue';
import HistoryCompact from '../../src/components/history-compact.vue';
import { normalizeHistoryTextFilter } from '../../src/utils/history';

const VueGoodTableStub = {
    props: ['columns', 'rows', 'totalRows', 'searchOptions', 'sortOptions', 'paginationOptions', 'columnFilterOptions', 'rowStyleClass', 'styleClass'],
    render(h) {
        const slot = this.$scopedSlots['column-filter'];
        const fields = ['episodeTitle', 'providerId', 'size'];
        return h('div', fields.map(field => slot ? slot({
            column: {
                field
            }
        }) : null));
    }
};

const consts = {
    qualities: {
        values: [{
            value: '1',
            text: 'test'
        }]
    },
    clientStatuses: [{
        value: 1,
        name: 'test'
    }, {
        value: 2,
        name: 'also'
    }]
};

const createLocalVueForHistory = () => {
    const localVue = createLocalVue();
    localVue.use(Vuex);
    return localVue;
};

const createHistoryStore = (history = {}) => {
    const {
        remote = {},
        remoteCompact = {},
        ...historyState
    } = history;
    const remoteStateDefaults = {
        page: 2,
        perPage: 25,
        sort: [{ field: 'date', type: 'desc' }],
        filter: {
            columnFilters: {}
        },
        rows: [],
        totalRows: 0
    };

    return new Vuex.Store({
        state: {},
        modules: {
            config: {
                state: {
                    consts
                }
            },
            history: {
                state: {
                    remote: {
                        ...remoteStateDefaults,
                        ...remote
                    },
                    remoteCompact: {
                        ...remoteStateDefaults,
                        ...remoteCompact
                    },
                    ...historyState
                }
            }
        },
        actions: {
            getHistory: jest.fn(),
            checkHistory: jest.fn(),
            setStoreLayout: jest.fn()
        },
        getters: {
            fuzzyParseDateTime: () => () => ''
        }
    });
};

const makeMountedHistoryComponent = (component, cookieStore = {}) => {
    const getCookie = jest.fn(key => {
        return cookieStore[key];
    });
    const setCookie = jest.fn((key, value) => {
        cookieStore[key] = value;
    });
    const loadItems = jest.fn();

    return {
        ...component,
        methods: {
            ...(component.methods || {}),
            getCookie,
            setCookie,
            loadItems
        },
        __testMocks: {
            getCookie,
            setCookie,
            loadItems
        }
    };
};

const mountDetailed = (history = {}) => {
    const localVue = createLocalVueForHistory();
    const store = createHistoryStore(history);
    const cookieStore = {};
    const component = makeMountedHistoryComponent(HistoryDetailed, cookieStore);

    const wrapper = shallowMount(component, {
        localVue,
        store,
        stubs: {
            VueGoodTable: VueGoodTableStub,
            AppLink: true,
            QualityPill: true,
            FontAwesomeIcon: true,
            Multiselect: true
        }
    });
    wrapper.vm.loadItemsDebounced = jest.fn();
    return {
        wrapper,
        store,
        cookieStore,
        ...component.__testMocks
    };
};

const mountCompact = (history = {}) => {
    const localVue = createLocalVueForHistory();
    const store = createHistoryStore(history);
    const cookieStore = {};
    const component = makeMountedHistoryComponent(HistoryCompact, cookieStore);

    const wrapper = shallowMount(component, {
        localVue,
        store,
        stubs: {
            VueGoodTable: VueGoodTableStub,
            AppLink: true,
            QualityPill: true
        }
    });

    wrapper.vm.loadItemsDebounced = jest.fn();
    return {
        wrapper,
        store,
        cookieStore,
        ...component.__testMocks
    };
};

const getPaginationOptions = wrapper => {
    const table = wrapper.vm.$children.find(child => {
        return child && child.$props && Object.prototype.hasOwnProperty.call(child.$props, 'paginationOptions');
    });
    return table && table.$props && table.$props.paginationOptions;
};

const detailedFilterDefaults = () => ({
    resource: 'old resource',
    providerId: 'old provider',
    quality: '720p',
    size: '< 1024',
    clientStatus: 1,
    statusName: 'Downloaded'
});

const detailedTextInput = field => field === 'resource' ? 'Show title or release' : 'Provider | Group';

const detailedTextMethod = field => field === 'resource' ? 'updateResource' : 'updateProvider';

const assertDetailedTextUpdate = async ({ field, value, expected, visibleValue = value, initialFilters = detailedFilterDefaults() }) => {
    const { wrapper } = mountDetailed({
        remote: {
            page: 9,
            filter: {
                columnFilters: initialFilters
            }
        }
    });
    wrapper.vm.loadItemsDebounced.mockClear();
    wrapper.vm[detailedTextMethod(field)]({
        currentTarget: {
            value
        }
    });
    await wrapper.vm.$nextTick();

    expect(wrapper.find(`input[placeholder="${detailedTextInput(field)}"]`).element.value).toBe(visibleValue);
    expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
        ...initialFilters,
        [field]: expected
    });
    expect(wrapper.vm.remoteHistory.page).toBe(1);
    expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
    wrapper.destroy();
};

const assertDetailedOtherFilter = async ({ method, event, field, expected }) => {
    const initialFilters = detailedFilterDefaults();
    const { wrapper } = mountDetailed({
        remote: {
            page: 9,
            filter: {
                columnFilters: initialFilters
            }
        }
    });
    wrapper.vm.updateResource({
        currentTarget: {
            value: "'  cleaned resource"
        }
    });
    wrapper.vm.loadItemsDebounced.mockClear();
    wrapper.vm[method](event);
    await wrapper.vm.$nextTick();

    expect(wrapper.find('input[placeholder="Show title or release"]').element.value).toBe('cleaned resource');
    expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
        ...initialFilters,
        resource: 'cleaned resource',
        [field]: expected
    });
    expect(wrapper.vm.remoteHistory.page).toBe(1);
    expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
    wrapper.destroy();
};

const assertCompactResourceUpdate = async ({ page, value, expected, existingFilters = { statusName: 'Downloaded' }, visibleValue = value }) => {
    const initialFilters = {
        resource: 'old compact',
        ...existingFilters
    };
    const { wrapper } = mountCompact({
        remoteCompact: {
            page,
            filter: {
                columnFilters: initialFilters
            }
        }
    });
    wrapper.vm.loadItemsDebounced.mockClear();
    wrapper.vm.updateResource({
        currentTarget: {
            value
        }
    });
    await wrapper.vm.$nextTick();

    expect(wrapper.find('input[placeholder="Show title or release"]').element.value).toBe(visibleValue);
    expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
        ...initialFilters,
        resource: expected
    });
    expect(wrapper.vm.remoteHistory.page).toBe(1);
    expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
    wrapper.destroy();
};

describe('normalizeHistoryTextFilter', () => {
    it('covers text boundary, punctuation, and Unicode normalization cases', () => {
        const cases = [
            ['', '', false, false],
            ['   ', '', false, false],
            ['  unquoted title  ', 'unquoted title', false, false],
            ["'  quoted title  '", "'  quoted title  '", false, false],
            ['"  quoted title  "', '"  quoted title  "', false, false],
            ['`  quoted title  `', '`  quoted title  `', false, false],
            ["  ''  ", '', false, true],
            ['""', '', false, true],
            ['``', '', false, true],
            ["'", '', true, false],
            ["'leading", 'leading', true, false],
            ['trailing"', 'trailing', true, false],
            ["'mismatched\"", 'mismatched', true, false],
            ["''leading", 'leading', true, false],
            ['trailing""', 'trailing', true, false],
            ["''  repeated  \"", 'repeated', true, false],
            ["Test's", "Test's", false, false],
            ["Test ' s", "Test ' s", false, false],
            ['Test"s', 'Test"s', false, false],
            ['Test " s', 'Test " s', false, false],
            ['Test`s', 'Test`s', false, false],
            ['Test ` s', 'Test ` s', false, false],
            ['"Test\'s"', '"Test\'s"', false, false],
            ["'Test \" s'", "'Test \" s'", false, false],
            ["  `Test ' s`  ", "`Test ' s`", false, false],
            ["'Dog Days\"'", "'Dog Days\"'", false, false],
            ['"Dog Days\'"', '"Dog Days\'"', false, false],
            ["'\"Leading double quote'", "'\"Leading double quote'", false, false],
            ['  ’The “Ogre” Bride’  ', '’The “Ogre” Bride’', false, false],
            ['  「日本語の題名」  ', '「日本語の題名」', false, false],
            ['  『Provider』  ', '『Provider』', false, false]
        ];

        cases.forEach(([value, filterValue, malformed, clearInput]) => {
            expect(normalizeHistoryTextFilter(value)).toEqual({
                filterValue,
                malformed,
                clearInput
            });
        });
    });

    it('retains exactly one matching wrapper pair around repeated wrapper content', () => {
        const cases = [["'''", "'"], ["''''", "''"], ['"""', '"'], ['""""', '""'], ['```', '`'], ['````', '``']];

        cases.forEach(([value, inner]) => {
            const result = normalizeHistoryTextFilter(value);
            expect(result).toEqual({
                filterValue: value,
                malformed: false,
                clearInput: false
            });
            expect(result.filterValue.slice(1, -1)).toBe(inner);
        });
    });
});

describe('History filter state composition', () => {
    it('detailed onColumnFilter merges native action changes while preserving manual filters', () => {
        const { wrapper, setCookie } = mountDetailed({
            remote: {
                page: 4,
                filter: {
                    columnFilters: {
                        resource: 'The Show',
                        providerId: 'provider-a',
                        quality: '1080p',
                        size: '< 1024',
                        clientStatus: 5,
                        statusName: 'Downloaded'
                    }
                }
            }
        });

        setCookie.mockClear();
        wrapper.vm.loadItemsDebounced.mockClear();

        wrapper.vm.onColumnFilter({
            columnFilters: {
                statusName: 'Failed'
            }
        });

        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.remoteHistory.filter).toEqual({
            columnFilters: {
                resource: 'The Show',
                providerId: 'provider-a',
                quality: '1080p',
                size: '< 1024',
                clientStatus: 5,
                statusName: 'Failed'
            }
        });
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        expect(setCookie).toHaveBeenCalledWith('filter', wrapper.vm.remoteHistory.filter);
        wrapper.destroy();
    });

    it('detailed pager options track page and remain on first page when episode/resource filter is set and cleared', async () => {
        const { wrapper } = mountDetailed({
            remote: {
                page: 4,
                filter: {
                    columnFilters: {
                        resource: 'The Show',
                        providerId: 'provider-a',
                        quality: '1080p',
                        size: '< 1024',
                        clientStatus: 5,
                        statusName: 'Downloaded'
                    }
                }
            }
        });

        wrapper.vm.loadItemsDebounced.mockClear();

        expect(getPaginationOptions(wrapper).setCurrentPage).toBe(4);

        wrapper.vm.onPageChange({
            currentPage: 2
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.remoteHistory.page).toBe(2);
        expect(getPaginationOptions(wrapper).setCurrentPage).toBe(2);
        wrapper.vm.loadItemsDebounced.mockClear();

        wrapper.vm.updateResource({
            currentTarget: {
                value: 'new resource'
            }
        });
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        await wrapper.vm.$nextTick();
        expect(getPaginationOptions(wrapper).setCurrentPage).toBe(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateResource({
            currentTarget: {
                value: ''
            }
        });
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        await wrapper.vm.$nextTick();
        expect(getPaginationOptions(wrapper).setCurrentPage).toBe(1);
        wrapper.destroy();
    });

    it('detailed onColumnFilter keeps statusName cleared and fully resets native keys on empty map', () => {
        const { wrapper } = mountDetailed({
            remote: {
                page: 3,
                filter: {
                    columnFilters: {
                        resource: 'The Show',
                        providerId: 'provider-a',
                        quality: '1080p',
                        size: '< 1024',
                        clientStatus: 5,
                        statusName: 'Downloaded'
                    }
                }
            }
        });

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.onColumnFilter({
            columnFilters: {
                statusName: ''
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
            resource: 'The Show',
            providerId: 'provider-a',
            quality: '1080p',
            size: '< 1024',
            clientStatus: 5,
            statusName: ''
        });
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        expect(wrapper.vm.remoteHistory.page).toBe(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.onColumnFilter({
            columnFilters: {}
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
            resource: 'The Show',
            providerId: 'provider-a',
            quality: '1080p',
            size: '< 1024',
            clientStatus: 5
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.statusName).toBeUndefined();
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        wrapper.destroy();
    });

    it('detailed manual filters preserve other fields and queue one load per valid update', () => {
        const { wrapper, setCookie } = mountDetailed({
            remote: {
                page: 9,
                filter: {
                    columnFilters: {
                        resource: 'old resource',
                        providerId: 'old provider',
                        quality: '720p',
                        size: '< 1024',
                        clientStatus: 1,
                        statusName: 'Downloaded'
                    }
                }
            }
        });
        setCookie.mockClear();

        wrapper.vm.updateResource({
            currentTarget: {
                value: 'new resource'
            }
        });
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
            resource: 'new resource',
            providerId: 'old provider',
            quality: '720p',
            size: '< 1024',
            clientStatus: 1,
            statusName: 'Downloaded'
        });
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateProvider({
            currentTarget: {
                value: 'new provider'
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.providerId).toBe('new provider');
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateQualityFilter({
            currentTarget: {
                value: '1080p'
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.quality).toBe('1080p');
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateClientStatusFilter([{
            value: 1
        }, {
            value: 2
        }]);
        expect(wrapper.vm.selectedClientStatusValue).toEqual([{
            value: 1
        }, {
            value: 2
        }]);
        expect(wrapper.vm.remoteHistory.filter.columnFilters.clientStatus).toBe(3);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateSizeFilter({
            currentTarget: {
                value: '> 2048'
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.size).toBe('> 2048');
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateSizeFilter({
            currentTarget: {
                value: ''
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.size).toBe('');
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateSizeFilter({
            currentTarget: {
                value: 'abc'
            }
        });
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(0);
        expect(setCookie).toHaveBeenCalledTimes(0);
        wrapper.destroy();
    });

    it('detailed provider filter trims outer whitespace and preserves the filter stack', () => {
        const initialFilters = {
            resource: 'old resource',
            providerId: 'old provider',
            quality: '720p',
            size: '< 1024',
            clientStatus: 1,
            statusName: 'Downloaded'
        };
        const { wrapper } = mountDetailed({
            remote: {
                page: 9,
                filter: {
                    columnFilters: initialFilters
                }
            }
        });
        const cases = [
            {
                value: '  leading provider',
                expected: 'leading provider'
            },
            {
                value: 'trailing provider  ',
                expected: 'trailing provider'
            },
            {
                value: '  both sides provider  ',
                expected: 'both sides provider'
            },
            {
                value: '   ',
                expected: ''
            }
        ];

        cases.forEach(({ value, expected }) => {
            wrapper.vm.loadItemsDebounced.mockClear();
            wrapper.vm.updateProvider({
                currentTarget: {
                    value
                }
            });
            expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
                ...initialFilters,
                providerId: expected
            });
            expect(wrapper.vm.remoteHistory.page).toBe(1);
            expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        });
        wrapper.destroy();
    });

    it('detailed episode and provider filters preserve quoted backend values', async () => {
        const { wrapper } = mountDetailed();

        wrapper.vm.updateResource({
            currentTarget: {
                value: "'  quoted episode  '"
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.resource).toBe("'  quoted episode  '");
        await wrapper.vm.$nextTick();
        expect(wrapper.find('input[placeholder="Show title or release"]').element.value).toBe("'  quoted episode  '");

        wrapper.vm.updateResource({
            currentTarget: {
                value: 'plain episode'
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.resource).toBe('plain episode');

        wrapper.vm.updateProvider({
            currentTarget: {
                value: '  "  quoted provider  "  '
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.providerId).toBe('"  quoted provider  "');
        await wrapper.vm.$nextTick();
        expect(wrapper.find('input[placeholder="Provider | Group"]').element.value).toBe('  "  quoted provider  "  ');

        wrapper.vm.updateProvider({
            currentTarget: {
                value: 'plain provider'
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.providerId).toBe('plain provider');
        wrapper.destroy();
    });

    it('detailed text inputs reflect existing remote filters on mount', async () => {
        const { wrapper } = mountDetailed({
            remote: {
                filter: {
                    columnFilters: {
                        resource: 'stored episode',
                        providerId: 'stored provider'
                    }
                }
            }
        });

        await wrapper.vm.$nextTick();
        expect([
            wrapper.find('input[placeholder="Show title or release"]').element.value,
            wrapper.find('input[placeholder="Provider | Group"]').element.value
        ]).toEqual(['stored episode', 'stored provider']);
        wrapper.destroy();
    });

    it('detailed text filters keep malformed wrappers raw-visible while storing cleaned values', () => {
        expect.assertions(8);
        const cases = [
            ['resource', "'  leading only", 'leading only'],
            ['providerId', 'trailing only"  ', 'trailing only']
        ];
        return Promise.all(cases.map(([field, value, expected]) => assertDetailedTextUpdate({
            field,
            value,
            expected
        })));
    });

    it('detailed text filters preserve matching wrappers, inner spaces, and internal punctuation', () => {
        expect.assertions(16);
        const cases = [
            ['resource', "'  The Ogre's Bride  '", "'  The Ogre's Bride  '"],
            ['providerId', '  "  Provider Group  "  ', '"  Provider Group  "'],
            ['resource', '  "  Dog Days\'  "  ', '"  Dog Days\'  "'],
            ['providerId', '  plain provider  ', 'plain provider']
        ];
        return Promise.all(cases.map(([field, value, expected]) => assertDetailedTextUpdate({
            field,
            value,
            expected
        })));
    });

    it('detailed empty matching pairs clear their stored and visible values', () => {
        expect.assertions(8);
        return Promise.all(['resource', 'providerId'].map(field => assertDetailedTextUpdate({
            field,
            value: "''",
            expected: '',
            visibleValue: ''
        })));
    });

    it('detailed successful manual filters canonicalize malformed text while preserving the stack', () => {
        expect.assertions(16);
        const cases = [
            ['updateQualityFilter', { currentTarget: { value: '1080p' } }, 'quality', '1080p'],
            ['updateSizeFilter', { currentTarget: { value: '  > 2048  ' } }, 'size', '> 2048'],
            ['updateSizeFilter', { currentTarget: { value: '   ' } }, 'size', ''],
            ['updateClientStatusFilter', [{ value: 1 }, { value: 2 }], 'clientStatus', 3]
        ];
        return Promise.all(cases.map(([method, event, field, expected]) => assertDetailedOtherFilter({
            method,
            event,
            field,
            expected
        })));
    });

    it('detailed cross-text and native filters canonicalize malformed inputs once', async () => {
        const initialFilters = {
            resource: 'old resource',
            providerId: 'old provider',
            quality: '720p',
            size: '< 1024',
            clientStatus: 1,
            statusName: 'Downloaded'
        };
        const { wrapper, setCookie } = mountDetailed({
            remote: {
                page: 9,
                filter: {
                    columnFilters: initialFilters
                }
            }
        });

        wrapper.vm.updateResource({
            currentTarget: {
                value: "'  cleaned resource"
            }
        });
        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateProvider({
            currentTarget: {
                value: '  "  provider group  "  '
            }
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
            ...initialFilters,
            resource: 'cleaned resource',
            providerId: '"  provider group  "'
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find('input[placeholder="Show title or release"]').element.value).toBe('cleaned resource');
        expect(wrapper.find('input[placeholder="Provider | Group"]').element.value).toBe('  "  provider group  "  ');
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.updateProvider({
            currentTarget: {
                value: "'  cleaned provider"
            }
        });
        wrapper.vm.loadItemsDebounced.mockClear();
        setCookie.mockClear();
        wrapper.vm.onColumnFilter({
            columnFilters: {
                statusName: 'Failed'
            }
        });

        return wrapper.vm.$nextTick().then(() => {
            expect(wrapper.find('input[placeholder="Provider | Group"]').element.value).toBe('cleaned provider');
            expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
                ...initialFilters,
                resource: 'cleaned resource',
                providerId: 'cleaned provider',
                statusName: 'Failed'
            });
            expect(wrapper.vm.remoteHistory.page).toBe(1);
            expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
            expect(setCookie).toHaveBeenCalledWith('filter', wrapper.vm.remoteHistory.filter);
            wrapper.destroy();
        });
    });

    it('detailed size filter canonicalizes valid values, including quoted values', () => {
        const initialFilters = {
            resource: 'old resource',
            providerId: 'old provider',
            quality: '720p',
            size: '< 1024',
            clientStatus: 1,
            statusName: 'Downloaded'
        };
        const { wrapper } = mountDetailed({
            remote: {
                page: 9,
                filter: {
                    columnFilters: initialFilters
                }
            }
        });
        const cases = [
            {
                value: '<1024',
                expected: '< 1024'
            },
            {
                value: '< 1024',
                expected: '< 1024'
            },
            {
                value: '  > 1024',
                expected: '> 1024'
            },
            {
                value: '> 1024  ',
                expected: '> 1024'
            },
            {
                value: '  > 1024  ',
                expected: '> 1024'
            },
            {
                value: "  '<1024'  ",
                expected: '< 1024'
            },
            {
                value: '  "> 8"  ',
                expected: '> 8'
            },
            {
                value: '`< 1`',
                expected: '< 1'
            },
            {
                value: '   ',
                expected: ''
            }
        ];

        cases.forEach(({ value, expected }) => {
            wrapper.vm.loadItemsDebounced.mockClear();
            wrapper.vm.updateSizeFilter({
                currentTarget: {
                    value
                }
            });
            expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
                ...initialFilters,
                size: expected
            });
            expect(wrapper.vm.remoteHistory.page).toBe(1);
            expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters.size).toBe('');
        wrapper.destroy();
    });

    it('detailed size filter rejects invalid values without changing state or loading', () => {
        const initialFilters = {
            resource: 'old resource',
            providerId: 'old provider',
            quality: '720p',
            size: '> 8',
            clientStatus: 1,
            statusName: 'Downloaded'
        };
        const { wrapper, setCookie } = mountDetailed({
            remote: {
                page: 9,
                filter: {
                    columnFilters: initialFilters
                }
            }
        });
        const filterBefore = JSON.parse(JSON.stringify(wrapper.vm.remoteHistory.filter));
        const invalidValues = [
            '= 1024',
            '<= 1024',
            '>= 1024',
            '< 1024 MB',
            '< 1024 OR 1=1',
            '< 1234567',
            "'< 1024\""
        ];

        invalidValues.forEach(value => {
            wrapper.vm.loadItemsDebounced.mockClear();
            setCookie.mockClear();
            wrapper.vm.updateSizeFilter({
                currentTarget: {
                    value
                }
            });
            expect(wrapper.vm.remoteHistory.filter).toEqual(filterBefore);
            expect(wrapper.vm.remoteHistory.page).toBe(9);
            expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(0);
            expect(setCookie).toHaveBeenCalledTimes(0);
        });
        wrapper.destroy();
    });

    it('detailed invalid size input leaves malformed text visible and does not reload', async () => {
        const { wrapper } = mountDetailed();
        const malformedResource = "'  still editing";
        wrapper.vm.updateResource({
            currentTarget: {
                value: malformedResource
            }
        });
        await wrapper.vm.$nextTick();
        const filterBefore = JSON.parse(JSON.stringify(wrapper.vm.remoteHistory.filter));
        wrapper.vm.loadItemsDebounced.mockClear();

        wrapper.vm.updateSizeFilter({
            currentTarget: {
                value: '<= 1024'
            }
        });
        await wrapper.vm.$nextTick();

        expect(wrapper.find('input[placeholder="Show title or release"]').element.value).toBe(malformedResource);
        expect(wrapper.vm.remoteHistory.filter).toEqual(filterBefore);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(0);
        wrapper.destroy();
    });

    it('detailed size filter clears matching quote-only values for each wrapper', () => {
        const { wrapper } = mountDetailed({
            remote: {
                filter: {
                    columnFilters: {
                        size: '> 8'
                    }
                }
            }
        });
        const quoteOnlyValues = ["''", '""', '``', "  ''  "];

        quoteOnlyValues.forEach(value => {
            wrapper.vm.loadItemsDebounced.mockClear();
            wrapper.vm.updateSizeFilter({
                currentTarget: {
                    value
                }
            });
            expect(wrapper.vm.remoteHistory.filter.columnFilters.size).toBe('');
            expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        });
        wrapper.destroy();
    });

    it('detailed manual update from null filter is safe', () => {
        const { wrapper } = mountDetailed({
            remote: {
                page: 6,
                filter: null
            }
        });

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateProvider({
            currentTarget: {
                value: 'provider-null-safe'
            }
        });

        expect(wrapper.vm.remoteHistory.filter).toEqual({
            columnFilters: {
                providerId: 'provider-null-safe'
            }
        });
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        wrapper.destroy();
    });

    it('compact resource filter preserves existing filter keys and only updates remoteCompact page', async () => {
        const sharedHistory = {
            remote: {
                page: 10,
                filter: {
                    columnFilters: {
                        statusName: 'Downloaded',
                        other: 'detail only'
                    }
                }
            },
            remoteCompact: {
                page: 7,
                filter: {
                    columnFilters: {
                        resource: 'old compact',
                        statusName: 'Downloaded'
                    }
                }
            }
        };
        const localVue = createLocalVueForHistory();
        const store = createHistoryStore(sharedHistory);
        const cookieStore = {};
        const detailedComponent = makeMountedHistoryComponent(HistoryDetailed, cookieStore);
        const compactComponent = makeMountedHistoryComponent(HistoryCompact, cookieStore);

        const detailed = shallowMount(detailedComponent, {
            localVue,
            store,
            stubs: {
                VueGoodTable: VueGoodTableStub,
                AppLink: true,
                QualityPill: true,
                FontAwesomeIcon: true,
                Multiselect: true
            }
        });
        const compact = shallowMount(compactComponent, {
            localVue,
            store,
            stubs: {
                VueGoodTable: VueGoodTableStub,
                AppLink: true,
                QualityPill: true
            }
        });
        const compactSetCookie = compactComponent.__testMocks.setCookie;
        const detailedSetCookie = detailedComponent.__testMocks.setCookie;
        compactSetCookie.mockClear();
        detailedSetCookie.mockClear();

        detailed.vm.loadItemsDebounced = jest.fn();
        compact.vm.loadItemsDebounced = jest.fn();

        await compact.vm.$nextTick();
        expect(compact.find('input[placeholder="Show title or release"]').element.value).toBe('old compact');
        expect(getPaginationOptions(compact).setCurrentPage).toBe(7);
        expect(getPaginationOptions(detailed).setCurrentPage).toBe(10);

        compact.vm.updateResource({
            currentTarget: {
                value: 'new compact'
            }
        });
        await compact.vm.$nextTick();

        expect(compact.vm.remoteHistory.page).toBe(1);
        expect(compact.vm.remoteHistory.filter.columnFilters).toEqual({
            resource: 'new compact',
            statusName: 'Downloaded'
        });
        expect(detailed.vm.remoteHistory.page).toBe(10);
        expect(detailed.vm.remoteHistory.filter).toEqual({
            columnFilters: {
                statusName: 'Downloaded',
                other: 'detail only'
            }
        });
        await compact.vm.$nextTick();
        expect(getPaginationOptions(compact).setCurrentPage).toBe(1);
        expect(getPaginationOptions(detailed).setCurrentPage).toBe(10);
        expect(compact.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        expect(detailed.vm.loadItemsDebounced).toHaveBeenCalledTimes(0);
        expect(compactSetCookie).toHaveBeenCalledTimes(0);
        expect(detailedSetCookie).toHaveBeenCalledTimes(0);
        detailed.destroy();
        compact.destroy();
    });

    it('compact resource filter trims unquoted input while retaining the raw value', async () => {
        expect.assertions(4);
        await assertCompactResourceUpdate({
            page: 6,
            value: '  compact title  ',
            expected: 'compact title',
            existingFilters: {
                statusName: 'Downloaded',
                clientStatus: 5
            }
        });
    });

    it('compact resource filter stores cleaned malformed input while retaining its raw value', async () => {
        expect.assertions(4);
        await assertCompactResourceUpdate({
            page: 4,
            value: "  'compact malformed",
            expected: 'compact malformed'
        });
    });

    it('compact resource filter preserves non-empty matching wrappers and inner spaces', async () => {
        expect.assertions(4);
        await assertCompactResourceUpdate({
            page: 3,
            value: '  "  compact title  "  ',
            expected: '"  compact title  "'
        });
    });

    it('compact resource filter clears each empty matching wrapper', async () => {
        expect.assertions(12);
        await assertCompactResourceUpdate({ page: 5, value: "''", expected: '', visibleValue: '' });
        await assertCompactResourceUpdate({ page: 5, value: '""', expected: '', visibleValue: '' });
        await assertCompactResourceUpdate({ page: 5, value: '``', expected: '', visibleValue: '' });
    });

    it('detailed mutations do not alter compact state', async () => {
        const sharedHistory = {
            remote: {
                page: 5,
                filter: {
                    columnFilters: {
                        resource: 'detailed-only',
                        providerId: 'detailed-provider',
                        clientStatus: 1,
                        quality: '720p',
                        size: '< 500',
                        statusName: 'Downloaded'
                    }
                }
            },
            remoteCompact: {
                page: 8,
                filter: {
                    columnFilters: {
                        resource: 'compact-only'
                    }
                }
            }
        };
        const localVue = createLocalVueForHistory();
        const store = createHistoryStore(sharedHistory);
        const cookieStore = {};
        const detailedComponent = makeMountedHistoryComponent(HistoryDetailed, cookieStore);
        const compactComponent = makeMountedHistoryComponent(HistoryCompact, cookieStore);

        const detailed = shallowMount(detailedComponent, {
            localVue,
            store,
            stubs: {
                VueGoodTable: VueGoodTableStub,
                AppLink: true,
                QualityPill: true,
                FontAwesomeIcon: true,
                Multiselect: true
            }
        });
        const compact = shallowMount(compactComponent, {
            localVue,
            store,
            stubs: {
                VueGoodTable: VueGoodTableStub,
                AppLink: true,
                QualityPill: true
            }
        });
        const compactSetCookie = compactComponent.__testMocks.setCookie;
        compactSetCookie.mockClear();

        detailed.vm.loadItemsDebounced = jest.fn();
        compact.vm.loadItemsDebounced = jest.fn();

        const compactPageBefore = compact.vm.remoteHistory.page;
        const compactFilterBefore = JSON.parse(JSON.stringify(compact.vm.remoteHistory.filter));
        await compact.vm.$nextTick();
        expect(getPaginationOptions(detailed).setCurrentPage).toBe(5);
        expect(getPaginationOptions(compact).setCurrentPage).toBe(8);
        detailed.vm.updateResource({
            currentTarget: {
                value: 'detailed-updated'
            }
        });
        expect(detailed.vm.remoteHistory.filter.columnFilters.resource).toBe('detailed-updated');
        expect(compact.vm.remoteHistory.page).toBe(compactPageBefore);
        expect(compact.vm.remoteHistory.filter).toEqual(compactFilterBefore);
        expect(compact.vm.remoteHistory.filter).not.toEqual(detailed.vm.remoteHistory.filter);
        expect(getPaginationOptions(compact).setCurrentPage).toBe(8);
        expect(getPaginationOptions(detailed).setCurrentPage).toBe(5);
        expect(detailed.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        expect(compact.vm.loadItemsDebounced).toHaveBeenCalledTimes(0);
        expect(compactSetCookie).toHaveBeenCalledTimes(0);
        compact.destroy();
        detailed.destroy();
    });

    it('compact mutations do not alter detailed state', async () => {
        const sharedHistory = {
            remote: {
                page: 5,
                filter: {
                    columnFilters: {
                        resource: 'detailed-only',
                        providerId: 'detailed-provider',
                        clientStatus: 1,
                        quality: '720p',
                        size: '< 500',
                        statusName: 'Downloaded'
                    }
                }
            },
            remoteCompact: {
                page: 8,
                filter: {
                    columnFilters: {
                        resource: 'compact-only'
                    }
                }
            }
        };
        const localVue = createLocalVueForHistory();
        const store = createHistoryStore(sharedHistory);
        const cookieStore = {};
        const detailedComponent = makeMountedHistoryComponent(HistoryDetailed, cookieStore);
        const compactComponent = makeMountedHistoryComponent(HistoryCompact, cookieStore);

        const detailed = shallowMount(detailedComponent, {
            localVue,
            store,
            stubs: {
                VueGoodTable: VueGoodTableStub,
                AppLink: true,
                QualityPill: true,
                FontAwesomeIcon: true,
                Multiselect: true
            }
        });
        const compact = shallowMount(compactComponent, {
            localVue,
            store,
            stubs: {
                VueGoodTable: VueGoodTableStub,
                AppLink: true,
                QualityPill: true
            }
        });
        const compactSetCookie = compactComponent.__testMocks.setCookie;
        compactSetCookie.mockClear();

        detailed.vm.loadItemsDebounced = jest.fn();
        compact.vm.loadItemsDebounced = jest.fn();

        const detailedPageBefore = detailed.vm.remoteHistory.page;
        const detailedFilterBefore = JSON.parse(JSON.stringify(detailed.vm.remoteHistory.filter));
        await compact.vm.$nextTick();
        expect(getPaginationOptions(compact).setCurrentPage).toBe(8);
        expect(getPaginationOptions(detailed).setCurrentPage).toBe(5);
        compact.vm.updateResource({
            currentTarget: {
                value: 'compact-updated'
            }
        });
        await compact.vm.$nextTick();
        expect(compact.vm.remoteHistory.filter.columnFilters.resource).toBe('compact-updated');
        expect(compact.vm.remoteHistory.page).toBe(1);
        expect(detailed.vm.remoteHistory.page).toBe(detailedPageBefore);
        expect(detailed.vm.remoteHistory.filter).toEqual(detailedFilterBefore);
        expect(getPaginationOptions(compact).setCurrentPage).toBe(1);
        expect(getPaginationOptions(detailed).setCurrentPage).toBe(5);
        expect(detailed.vm.loadItemsDebounced).toHaveBeenCalledTimes(0);
        expect(compact.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        expect(compactSetCookie).toHaveBeenCalledTimes(0);
        compact.destroy();
        detailed.destroy();
    });

    it('compact onColumnFilter keeps resource and replaces/clears native keys with page reset and one load', () => {
        const { wrapper, setCookie } = mountCompact({
            remoteCompact: {
                page: 6,
                filter: {
                    columnFilters: {
                        resource: 'compact show',
                        statusName: 'Downloaded',
                        clientStatus: 5
                    }
                }
            }
        });
        setCookie.mockClear();

        wrapper.vm.onColumnFilter({
            columnFilters: {
                statusName: 'Failed'
            }
        });

        expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
            resource: 'compact show',
            statusName: 'Failed'
        });
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.onColumnFilter({
            columnFilters: {}
        });
        expect(wrapper.vm.remoteHistory.filter.columnFilters).toEqual({
            resource: 'compact show'
        });
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        expect(setCookie).toHaveBeenCalledTimes(0);
        wrapper.destroy();
    });

    it('compact pager options track page and remain on first page when episode/resource filter is set and cleared', async () => {
        const { wrapper } = mountCompact({
            remoteCompact: {
                page: 6,
                filter: {
                    columnFilters: {
                        resource: 'compact show',
                        statusName: 'Downloaded',
                        clientStatus: 5
                    }
                }
            }
        });

        wrapper.vm.loadItemsDebounced.mockClear();

        expect(getPaginationOptions(wrapper).setCurrentPage).toBe(6);

        wrapper.vm.onPageChange({
            currentPage: 3
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.remoteHistory.page).toBe(3);
        expect(getPaginationOptions(wrapper).setCurrentPage).toBe(3);
        wrapper.vm.loadItemsDebounced.mockClear();

        wrapper.vm.updateResource({
            currentTarget: {
                value: 'new compact resource'
            }
        });
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        await wrapper.vm.$nextTick();
        expect(getPaginationOptions(wrapper).setCurrentPage).toBe(1);

        wrapper.vm.loadItemsDebounced.mockClear();
        wrapper.vm.updateResource({
            currentTarget: {
                value: ''
            }
        });
        expect(wrapper.vm.remoteHistory.page).toBe(1);
        expect(wrapper.vm.loadItemsDebounced).toHaveBeenCalledTimes(1);
        await wrapper.vm.$nextTick();
        expect(getPaginationOptions(wrapper).setCurrentPage).toBe(1);
        wrapper.destroy();
    });

    it('both components render the Episode filter placeholder as Show title or release', () => {
        const { wrapper: detailed } = mountDetailed();
        const { wrapper: compact } = mountCompact();

        expect(detailed.find('input[placeholder="Show title or release"]').exists()).toBe(true);
        expect(compact.find('input[placeholder="Show title or release"]').exists()).toBe(true);
        detailed.destroy();
        compact.destroy();
    });

    it('detailed Size filter placeholder uses an unquoted example', () => {
        const { wrapper } = mountDetailed();

        expect(wrapper.find('input[placeholder="e.g. < 1024 MB"]').exists()).toBe(true);
        expect(wrapper.find('input[placeholder*="`"]').exists()).toBe(false);
        wrapper.destroy();
    });
});
