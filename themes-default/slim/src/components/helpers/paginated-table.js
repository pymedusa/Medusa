import { VueGoodTable } from 'vue-good-table';
import TablePageSize from './table-page-size.vue';

const NativePagination = VueGoodTable.components['vgt-pagination'];

const Pagination = {
    extends: NativePagination,
    methods: {
        updatePageSize(value) {
            if (value === this.currentPerPage) {
                return;
            }
            this.currentPerPage = value;
            this.perPageChanged(true);
        }
    },
    render(h) {
        // The pinned vue-good-table footer render has a vgt-wrap__footer root.
        const footer = NativePagination.render.call(this, h);
        footer.children.unshift(h(TablePageSize, {
            props: {
                id: this.id,
                value: this.currentPerPage,
                options: this.customRowsPerPageDropdown.filter(size => size > 0)
            },
            on: { input: this.updatePageSize }
        }));
        return footer;
    }
};

export default {
    extends: VueGoodTable,
    components: { 'vgt-pagination': Pagination }
};
