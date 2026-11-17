import Vuex, { Store } from 'vuex';
import { createLocalVue, shallowMount } from '@vue/test-utils';
import ShowHeader from '../../src/components/show-header.vue';
import constsModule from '../../src/store/modules/config/consts';
import showsModule from '../../src/store/modules/shows';
import fixtures from '../__fixtures__/common';
import showFixture from '../__fixtures__/show-detailed';

jest.mock('../../src/utils/jquery', () => ({ attachImdbTooltip: jest.fn() }));

describe('Show header recorded size', () => {
    let show;
    let wrapper;

    beforeEach(() => {
        show = { ...JSON.parse(JSON.stringify(showFixture)), seasons: [], size: 418670005 };
    });

    afterEach(() => {
        if (wrapper) {
            wrapper.destroy();
        }
    });

    const renderHeader = () => {
        const localVue = createLocalVue();
        localVue.use(Vuex);
        const { state } = JSON.parse(JSON.stringify(fixtures));
        const store = new Store({
            state,
            modules: {
                consts: {
                    state: state.config.consts,
                    getters: constsModule.getters
                },
                shows: {
                    state: { shows: [show], currentShow: { showSlug: show.id.slug } },
                    getters: showsModule.getters
                }
            }
        });

        wrapper = shallowMount(ShowHeader, {
            localVue,
            store,
            propsData: { slug: show.id.slug }
        });

        return wrapper.findAll('#show-summary tr').filter(row => row.find('td').text() === 'Size:');
    };

    it('keeps the recorded total visible when the show directory is missing', () => {
        show.config.locationValid = false;
        const sizeRows = renderHeader();

        expect(sizeRows).toHaveLength(1);
        expect(sizeRows.at(0).findAll('td').at(1).text()).toBe('399.27 MB');
        expect(wrapper.text()).toContain('(Missing)');
    });

    it('shows a recorded zero size even when the directory is missing', () => {
        show.config.locationValid = false;
        show.size = 0;
        const sizeRows = renderHeader();

        expect(sizeRows).toHaveLength(1);
        expect(sizeRows.at(0).findAll('td').at(1).text()).toBe('0.00 B');
    });

    it.each([null, undefined, -1])('does not present an unavailable size (%s) as zero', size => {
        show.size = size;

        expect(renderHeader()).toHaveLength(0);
    });

    it('uses the backend total when only part of the episode list is loaded', () => {
        show.size = 2 * (1024 ** 2);
        show.seasons = [{
            season: 1,
            children: [{ status: 'Downloaded', quality: 8, file: { size: 1024 } }]
        }];
        const sizeRows = renderHeader();

        expect(sizeRows.at(0).findAll('td').at(1).text()).toBe('2.00 MB');
    });
});
