import test from 'ava';
import { createLocalVue, mount } from '@vue/test-utils';
import { NamePattern } from '../../static/js/templates';

test.beforeEach(t => {
    t.context.localVue = createLocalVue();
});

test('renders', t => {
    const { localVue } = t.context;
    const wrapper = mount(NamePattern, {
        localVue,
        propsData: {
            namingPattern: 'S%0SE%0E - %EN',
            namingPresets: [
                { pattern: '%SN - %Sx%0E - %EN', example: 'Show Name - 2x03 - Ep Name' },
                { pattern: '%S.N.S%0SE%0E.%E.N', example: 'Show.Name.S02E03.Ep.Name' },
                { pattern: '%Sx%0E - %EN', example: '2x03 - Ep Name' },
                { pattern: 'S%0SE%0E - %EN', example: 'S02E03 - Ep Name' },
                { pattern: 'Season %0S/%S.N.S%0SE%0E.%Q.N-%RG', example: 'Season 02/Show.Name.S02E03.720p.HDTV-RLSGROUP' }
            ],
            type: '',
            multiEpStyle: 1,
            animeNamingType: 0
        },
        methods: {
            checkNaming() {
                return Promise.resolve();
            },
            testNaming() {
                return Promise.resolve('MockTestNamingResult');
            }
        }
    });

    t.snapshot(wrapper.html());
});
