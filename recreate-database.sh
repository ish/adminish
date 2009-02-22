echo -e "\n\tPrepared to replace adminish\n"
read -p "Continue? (yes/no): " REPLACE
if [ "$REPLACE" == "yes" ] || [ "$REPLACE" == "Yes" ] || [ "$REPLACE" == "YES" ]; then
echo -n "Deleting adminish .. "
curl -X DELETE http://localhost:5984/adminish
echo
echo -n "Creating adminish .. "
curl -X PUT http://localhost:5984/adminish
echo
./setup-app.sh
echo 'Populating Categories'
./populate_categories.sh adminish -v
echo
fi

