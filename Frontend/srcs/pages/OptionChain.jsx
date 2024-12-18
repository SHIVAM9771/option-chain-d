import React from "react";
import { FaChartLine, FaCalendarAlt, FaTable } from "react-icons/fa";
import SpotData from "../components/SpotData";
import OptionsTable from "../components/OptionsTable";
import DateList from "../components/DateList";
import Spinner from "../components/Spinner";
import { useSelector } from "react-redux";

function OptionChain() {
  const data = useSelector((state) => state.data.data);
  const theme = useSelector((state) => state.theme.theme);

  return (
    <div
      className={`min-h-screen flex flex-col items-center ${theme === "dark" ? "bg-gray-900" : "bg-gray-100"}`}
    >
      <div className="w-full max-w-full px-2 py-1">
        {data ? (
          <>
            <div
              className={` mb-1 shadow-lg rounded-lg relative transition-all ${theme === "dark" ? "bg-gray-800" : "bg-white"}`}
            >
              {/* <h2 className={`font-semibold flex bg-transparent absolute top-[-2px] left-2 ${theme === "dark" ? "bg-gray-800 text-gray-100" : "bg-white text-gray-950"} px-2 text-sm `}>
                <FaCalendarAlt className="mr-2 text-green-600" size={16} />
                Expiry Date
              </h2> */}
              <DateList />
            </div>


            <div
              className={`flex flex-col mb-10 bg-white shadow-lg  rounded-lg overflow-hidden transition-all ${theme === "dark" ? "bg-gray-800" : "bg-white"}`}
            >
              <OptionsTable />
            </div>

            <div
              className={`p-1  shadow-lg rounded-lg transition-all ${theme === "dark" ? "bg-gray-800" : "bg-white"}`}
            >
              <h2 className="font-semibold flex items-center">
                <FaChartLine className="mr-2 text-blue-600" size={16} />
                Spot Data
              </h2>
              <SpotData />
            </div>
          </>
        ) : (
          <div
            className={`rounded-lg shadow-md p-6 mb-0.5 text-center transition-all ${theme === "dark" ? "bg-gray-700 text-gray-300" : "bg-white text-gray-800"}`}
            role="status"
            aria-live="polite"
          >
            <Spinner />
            <p className="mt-4 text-lg">Loading data, please wait...</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default OptionChain;