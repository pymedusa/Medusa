import HistoryCompact from '../../src/components/history-compact.vue';
import HistoryDetailed from '../../src/components/history-detailed.vue';

describe('History compact corrections', () => {
    const labels = ['Time', 'Episode', 'Snatched', 'Downloaded', 'Subtitled', 'Quality'];

    it('reads visibility cookies using each column label', () => {
        const getCookie = jest.fn(label => `hidden:${label}`);
        const { columns } = HistoryCompact.data.call({ getCookie });

        expect(getCookie.mock.calls).toEqual(labels.map(label => [label]));
        expect(columns.map(column => ({ label: column.label, hidden: column.hidden }))).toEqual(
            labels.map(label => ({ label, hidden: `hidden:${label}` }))
        );
    });

    it('writes visibility cookies using the column labels through the mixin watcher', () => {
        const setCookie = jest.fn();
        const watch = jest.fn();
        const watcherContext = { $watch: watch, setCookie };

        HistoryCompact.mixins[0].created.call(watcherContext);
        const columnWatcher = watch.mock.calls[0][1];
        const columns = labels.map((label, index) => ({ label, hidden: index % 2 === 0 }));

        columnWatcher(columns);

        expect(setCookie.mock.calls).toEqual(columns.map(column => [column.label, column.hidden]));
    });

    it('sorts dated rows newest first and missing dates last without mutation', () => {
        const rows = [
            { id: 20, actionDate: null },
            { id: 3, actionDate: '20200101000000' },
            { id: 5, actionDate: 'not-a-date' },
            { id: 8, actionDate: '20230101000000' },
            { id: 1, actionDate: undefined },
            { id: 2, actionDate: '' },
            { id: 4, actionDate: 20230101000000 },
            { id: 6, actionDate: ' ' },
            { id: 7, actionDate: '20200101000000' }
        ];
        const originalRows = rows.map(row => ({ ...row }));

        const sortedRows = HistoryCompact.methods.sortDate(rows);

        expect(sortedRows).not.toBe(rows);
        expect(sortedRows.map(row => row.id)).toEqual([4, 8, 3, 7, 1, 2, 5, 6, 20]);
        expect(rows).toEqual(originalRows);
    });

    it('falls back for malformed Compact sort cookies', () => {
        const invalidSorts = [
            null,
            undefined,
            [],
            {},
            'raw-sort',
            [null],
            [{}],
            [{ field: 'date' }],
            [{ type: 'asc' }],
            [{ field: 'episodeTitle', type: 'asc' }],
            [{ field: 'date', type: 'none' }],
            [{ field: 1, type: 'asc' }],
            [{ field: 'date', type: 1 }]
        ];

        for (const invalidSort of invalidSorts) {
            const result = HistoryCompact.methods.getSortFromCookie.call({ getCookie: () => invalidSort });
            expect(result).toEqual([{ field: 'date', type: 'desc' }]);
        }
    });

    it('falls back for malformed Detailed sort cookies', () => {
        const invalidSorts = [
            null,
            undefined,
            [],
            {},
            'raw-sort',
            [null],
            [{}],
            [{ field: 'date' }],
            [{ type: 'asc' }],
            [{ field: 'subtitled', type: 'asc' }],
            [{ field: 'date', type: 'none' }],
            [{ field: 1, type: 'asc' }],
            [{ field: 'date', type: 1 }]
        ];

        for (const invalidSort of invalidSorts) {
            const result = HistoryDetailed.methods.getSortFromCookie.call({ getCookie: () => invalidSort });
            expect(result).toEqual([{ field: 'date', type: 'desc' }]);
        }
    });

    it('restores valid field and type pairs without mutating the cookie', () => {
        const validSorts = [
            [HistoryCompact, 'date', 'asc'],
            [HistoryCompact, 'actionDate', 'desc'],
            [HistoryCompact, 'subtitled', 'asc'],
            [HistoryCompact, 'quality', 'desc'],
            [HistoryDetailed, 'date', 'asc'],
            [HistoryDetailed, 'actionDate', 'desc'],
            [HistoryDetailed, 'statusName', 'asc'],
            [HistoryDetailed, 'quality', 'desc'],
            [HistoryDetailed, 'providerId', 'asc'],
            [HistoryDetailed, 'size', 'desc'],
            [HistoryDetailed, 'clientStatus', 'asc']
        ];

        for (const [component, field, type] of validSorts) {
            const sortCookie = [{ field, type }, { field: 'quality', type: 'desc' }];
            const originalSortCookie = sortCookie.map(sort => ({ ...sort }));
            const result = component.methods.getSortFromCookie.call({ getCookie: () => sortCookie });

            expect(result).toEqual([{ field, type }]);
            expect(result).not.toBe(sortCookie);
            expect(result[0]).not.toBe(sortCookie[0]);
            expect(sortCookie).toEqual(originalSortCookie);
        }
    });

    it('keeps the Compact and Detailed sort-cookie namespaces distinct', () => {
        const compactCookies = { get: jest.fn() };
        const detailedCookies = { get: jest.fn() };

        HistoryCompact.mixins[0].methods.getCookie.call({ $cookies: compactCookies }, 'sort');
        HistoryDetailed.mixins[0].methods.getCookie.call({ $cookies: detailedCookies }, 'sort');

        expect(compactCookies.get).toHaveBeenCalledWith('historyCompact-sort');
        expect(detailedCookies.get).toHaveBeenCalledWith('history-detailed-sort');
    });
});
