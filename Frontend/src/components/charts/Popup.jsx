import { useState } from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, LineElement, PointElement, CategoryScale, LinearScale, Tooltip, Legend, Title } from 'chart.js';
import zoomPlugin from 'chartjs-plugin-zoom';
import { FaTimes } from 'react-icons/fa';
import PropTypes from 'prop-types';
import { useSelector } from 'react-redux';
import { formatChartNumber } from '../../utils/utils';

// Register Chart.js modules and plugins
ChartJS.register(LineElement, PointElement, CategoryScale, LinearScale, Tooltip, Legend, Title, zoomPlugin);

const DeltaPopup = ({ data, onClose }) => {
    const theme = useSelector((state) => state.theme.theme);
    const [activeSection, setActiveSection] = useState('IV');

    if (!data) return null;

    const themeColors = {
        background: theme === 'dark' ? 'bg-gray-800' : 'bg-teal-400',
        text: theme === 'dark' ? '#e0e0e0' : '#333',
        gridColor: theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
    };

    const formatTimestamps = (timestamps) =>
        timestamps.map((ts) => new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    const shortTimeLabels = formatTimestamps(data.timestamp);

    const createDataset = (label, data, color, hidden = false) => ({
        label,
        data,
        borderColor: color,
        backgroundColor: color.replace('1)', '0.2)'),
        fill: false,
        pointRadius: 0,
        borderWidth: 1,
        tension: 0.1,
        hidden, // Default hidden state
    });

    const chartData = {
        labels: shortTimeLabels,
        datasets:
            activeSection === 'IV'
                ? [
                    createDataset('CE IV', data.ce_iv, 'rgba(255, 0, 0, 1)'),
                    createDataset('PE IV', data.pe_iv, 'rgba(0, 255, 0, 1)'),
                ]
                : [
                    createDataset('CE DELTA', data.ce_delta, 'rgba(255, 0, 0, 1)'),
                    createDataset('PE DELTA', data.pe_delta, 'rgba(0, 255, 0, 1)'),
                    createDataset('CE GAMMA', data.ce_theta, 'rgba(255, 0, 0, 1)', true),
                    createDataset('PE GAMMA', data.pe_theta, 'rgba(0, 255, 0, 1)', true),
                    createDataset('CE THETHA', data.ce_gamma, 'rgba(255, 0, 0, 1)', true),
                    createDataset('PE THETHA', data.pe_gamma, 'rgba(0, 255, 0, 1)', true),
                    createDataset('CE VEGA', data.ce_vega, 'rgba(255, 0, 0, 1)', true),
                    createDataset('PE VEGA', data.pe_vega, 'rgba(0, 255, 0, 1)', true),
                ]
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    color: themeColors.text,
                    font: {
                        size: 16,
                        family: 'Courier New, monospace',
                    },
                    padding: 2,
                    boxWidth: 10,
                    boxHeight: 10,
                },
                onHover: (event, legendItem) => {
                    const label = event.native.target;
                    label.style.cursor = 'pointer';
                    label.style.fontSize = '16px';
                    label.style.color = 'rgba(255, 0, 0, 1)'; // Changes color on hover
                },
                onLeave: (event) => {
                    const label = event.native.target;
                    label.style.fontSize = '12px';
                    label.style.color = themeColors.text;
                },
            },
            tooltip: {
                mode: 'nearest',
                intersect: false,
            },
            zoom: {
                zoom: {
                    wheel: { enabled: true },
                    pinch: { enabled: true },
                    mode: 'xy',
                },
                pan: { enabled: true, mode: 'xy' },
            },
        },
        scales: {
            x: {
                ticks: { color: themeColors.text },
                grid: { color: themeColors.gridColor },
            },
            y: {
                ticks: { color: themeColors.text },
                grid: { color: themeColors.gridColor },
            },
        },
    };


    return (
        <div
            className={`fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 ${themeColors.background}  rounded-lg p-4 w-[97%] h-[95%] z-50`}
            role="dialog"
            aria-modal="true"
        >
            <div className="flex flex-col items-center relative w-full h-full">
                <button onClick={onClose} aria-label="Close Popup" className="absolute top-1 right-2 text-gray-800 hover:text-gray-600">
                    <FaTimes size={24} color={themeColors.text} />
                </button>
                <p className={`text-2xl font-bold ${themeColors.text}`}>
                    {data.strike} {data.isCe ? 'CE' : 'PE'}
                </p>

                <div className="flex justify-center gap-4 my-4">
                    <p
                        onClick={() => setActiveSection('IV')}
                        className={`py-0 cursor-pointer px-4 rounded ${activeSection === 'IV' ? 'bg-white text-gray-800' : 'bg-gray-500 text-gray-200'}`}
                    >
                        IV
                    </p>
                    <p
                        onClick={() => setActiveSection('GREEKS')}
                        className={`py-0 cursor-pointer px-4 rounded ${activeSection === 'GREEKS' ? 'bg-white text-gray-800' : 'bg-gray-500 text-gray-200'}`}
                    >
                        GREEKS
                    </p>
                    {/* <p
            onClick={() => setActiveSection('Volume')}
            className={`py-0 cursor-pointer px-4 rounded ${activeSection === 'Volume' ? 'bg-white text-gray-800' : 'bg-gray-500 text-gray-200'}`}
          >
            Volume
          </p> */}
                </div>

                <div className="w-full h-full p-4">
                    <Line data={chartData} options={chartOptions} />
                </div>
            </div>
        </div>
    );
};

DeltaPopup.propTypes = {
    data: PropTypes.object,
    onClose: PropTypes.func.isRequired,
};

export default DeltaPopup;