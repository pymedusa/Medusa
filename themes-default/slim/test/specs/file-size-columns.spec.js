import { shallowMount } from '@vue/test-utils';
import { VueGoodTable } from 'vue-good-table';
import CurrentDownloads from '../../src/components/current-downloads.vue';
import DisplayShow from '../../src/components/display-show.vue';
import HistoryDetailed from '../../src/components/history-detailed.vue';
import ManageFailedDownloads from '../../src/components/manage-failed-downloads.vue';
import ShowHistory from '../../src/components/show-history.vue';
import ShowResults from '../../src/components/show-results.vue';

describe('File size table columns', () => {
    const components = [
        CurrentDownloads,
        DisplayShow,
        HistoryDetailed,
        ManageFailedDownloads,
        ShowHistory,
        ShowResults
    ];

    components.forEach(component => {
        it(`renders binary file sizes in ${component.name}`, () => {
            const { columns } = component.data.call({ getCookie: () => false });
            const sizeColumn = columns.find(column => column.label === 'Size');
            // Include the file size reported in issue #11108.
            const rows = [0, 1024, 418670005].map(size => ({ size, file: { size } }));
            const wrapper = shallowMount(VueGoodTable, {
                propsData: {
                    columns: [sizeColumn],
                    rows
                }
            });

            expect(wrapper.findAll('tbody td').wrappers.map(cell => cell.text())).toEqual([
                '0.00 B',
                '1.00 KB',
                '399.27 MB'
            ]);
            wrapper.destroy();
        });
    });
});
